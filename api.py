# =============================================================================
# api.py
# The Body Shop — Virtual Skincare Consultant  |  REST API Layer
#
# Wraps the LangGraph Plan-and-Execute agent (agent.py) in a FastAPI server
# so any HTTP client (the HTML/JS frontend) can talk to it.
#
# Architecture:
#   • FastAPI + uvicorn for the ASGI server
#   • CORSMiddleware — permits all origins for local frontend dev
#   • Lifespan manager — boots a psycopg_pool.ConnectionPool on startup,
#     initialises PostgresSaver + memory.setup(), injects the checkpointer
#     into the compiled graph, and tears everything down on shutdown
#   • POST /chat — accepts { session_id, message }, runs graph.invoke(),
#     returns { reply }
#
# Usage:
#   uvicorn api:app --reload --host 0.0.0.0 --port 8000
# =============================================================================

import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import psycopg2
import psycopg2.extras

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_core.messages import HumanMessage, AIMessage

# ---------------------------------------------------------------------------
# The compiled-but-checkpointer-less graph from agent.py.
# build_graph() is re-called inside the lifespan with memory injected, so
# this import is just to pull the builder function into scope.
# ---------------------------------------------------------------------------
from agent import build_graph


# =============================================================================
# SECTION 1 — PYDANTIC MODELS
# =============================================================================

class ChatRequest(BaseModel):
    """Payload the frontend POSTs to /chat."""
    session_id: str   # Acts as thread_id — scopes LangGraph checkpoints
    message:    str   # The raw user message


class ChatResponse(BaseModel):
    """Payload returned to the frontend."""
    reply: str        # The agent's final natural-language response


# =============================================================================
# SECTION 2 — APPLICATION STATE
#
# A plain namespace to hold the objects that must survive across requests:
#   • pool  — the psycopg_pool.ConnectionPool (async-friendly)
#   • graph — the compiled LangGraph with PostgresSaver injected
#
# Stored on app.state so every route handler can reach them via `request.app`.
# =============================================================================

class _AppState:
    conn:  object = None
    graph: object = None

app_state = _AppState()


# =============================================================================
# SECTION 3 — LIFESPAN MANAGER
#
# FastAPI calls the code BEFORE `yield` on startup and the code AFTER `yield`
# on shutdown. This is the right place for expensive one-time initialisation.
#
# Startup sequence:
#   1. Open a psycopg_pool.ConnectionPool (sync pool; PostgresSaver uses it)
#   2. Wrap it in PostgresSaver
#   3. Call memory.setup() — idempotent; creates checkpoint tables if absent
#   4. Compile the LangGraph with the checkpointer injected
#
# Shutdown sequence:
#   5. Close the connection pool gracefully
#
# NOTE on prepare_threshold / pgbouncer:
#   Supabase's pgbouncer (port 6543) rejects server-side prepared statements.
#   ConnectionPool accepts connection_kwargs which are forwarded to every new
#   psycopg connection — set prepare_threshold=0 here to disable prepared
#   statements globally for the pool, matching the fix used in the CLI loop.
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Boot the Postgres connection + LangGraph checkpointer on startup."""

    from psycopg import Connection as Psycopg3Connection
    from langgraph.checkpoint.postgres import PostgresSaver

    POSTGRES_URI = os.getenv("POSTGRES_URI")
    if not POSTGRES_URI:
        raise RuntimeError(
            "POSTGRES_URI is not set. "
            "Add it to your .env file before starting the API server."
        )

    # ------------------------------------------------------------------
    # Open a raw psycopg3 connection — identical pattern to the working
    # CLI script in agent.py __main__.
    #
    # WHY not ConnectionPool:
    #   PostgresSaver internally opens its own cursors and prepares
    #   statements regardless of the pool's kwargs, so even with
    #   prepare_threshold=0 on the pool the checkpointer itself trips
    #   the pgbouncer "prepared statement already exists" error.
    #   Passing a single manually-opened connection bypasses the pool
    #   layer entirely and gives PostgresSaver a connection where psycopg3
    #   has been told at the driver level to never prepare anything.
    #
    # prepare_threshold=0  — psycopg3 never promotes any query to a
    #                         server-side prepared statement. This is the
    #                         only reliable way to silence the collision
    #                         with Supabase's pgbouncer pooler.
    # autocommit=True      — required by PostgresSaver; it manages its
    #                         own transaction boundaries internally.
    # ------------------------------------------------------------------
    pg_conn = Psycopg3Connection.connect(
        POSTGRES_URI,
        autocommit=True,
        prepare_threshold=0,
    )

    # Clear any stale prepared statements left on a recycled pgbouncer
    # backend connection — safe no-op on a fresh connection.
    pg_conn.execute("DEALLOCATE ALL", prepare=False)

    memory = PostgresSaver(pg_conn)

    # Idempotent: creates checkpoint tables on first run, no-op thereafter.
    memory.setup()
    print("✅  Checkpoint store ready (Supabase Postgres).")

    # Compile the graph with persistent memory injected.
    app_state.conn  = pg_conn
    app_state.graph = build_graph(memory)
    print("✅  LangGraph compiled with PostgresSaver checkpointer.")

    yield  # ── server is live and handling requests ──────────────────

    # ------------------------------------------------------------------
    # Shutdown: close the connection cleanly.
    # ------------------------------------------------------------------
    pg_conn.close()
    print("🛑  Postgres connection closed.")


# =============================================================================
# SECTION 4 — FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="The Body Shop — Skincare Consultant API",
    description="REST wrapper around the LangGraph Plan-and-Execute agent.",
    version="1.0.0",
    lifespan=lifespan,
)


# =============================================================================
# SECTION 5 — CORS MIDDLEWARE
#
# Allow all origins so the local HTML/JS frontend (file://, localhost:*) can
# call the API without browser CORS errors.
# ⚠️  Restrict allow_origins to your production domain before going live.
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Local dev: permit everything
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# SECTION 6 — ENDPOINTS
# =============================================================================

@app.get("/health", tags=["meta"])
async def health_check():
    """Quick liveness probe — returns 200 if the server is up."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse, tags=["agent"])
async def chat(request: ChatRequest):
    """
    Send a message to the Virtual Skincare Consultant.

    - **session_id**: Unique identifier for the conversation thread.
      Returning the same session_id resumes the previous conversation
      (LangGraph loads the checkpoint from Postgres automatically).
    - **message**: The user's raw text input.
    """

    graph = app_state.graph
    if graph is None:
        # Should never happen if the lifespan ran correctly.
        raise HTTPException(
            status_code=503,
            detail="Agent graph is not initialised. Check server startup logs.",
        )

    # ------------------------------------------------------------------
    # Build the initial AgentState for this turn.
    #
    # • messages     — full conversation history retrieved from the
    #                  checkpointer, with the new HumanMessage appended.
    #                  This fixes Issue 1 (Context Amnesia): previously the
    #                  messages array was overwritten with only the newest
    #                  HumanMessage each turn, discarding all prior history.
    # • phone_number — explicitly set to request.session_id so the agent's
    #                  internal tools (cart, loyalty points, etc.) always
    #                  resolve to the correct customer account. This fixes
    #                  Issue 2 (Cart / Session Sync).
    # • plan / past_steps / response — reset each turn; the checkpointer
    #                  restores durable message history from Postgres.
    # ------------------------------------------------------------------

    # thread_id scopes all Postgres checkpoints to this session.
    config = {"configurable": {"thread_id": request.session_id}}

    # Fetch existing checkpoint state so we can prepend prior messages.
    current_state = graph.get_state(config)
    history = (
        current_state.values.get("messages", [])
        if current_state and current_state.values
        else []
    )

    # Append the new human turn to the recovered history.
    history.append(HumanMessage(content=request.message))

    initial_state = {
        "messages":     history,
        "plan":         [],
        "past_steps":   [],
        "response":     "",
        "phone_number": request.session_id,   # Issue 2: always mirrors session_id
    }

    try:
        final_state = graph.invoke(initial_state, config=config)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {exc}",
        )

    reply = final_state.get("response") or ""

    if not reply:
        # Replanner produced no final response — surface a safe fallback.
        reply = (
            "I'm sorry, I wasn't able to generate a response for that. "
            "Could you please rephrase your question?"
        )

    return ChatResponse(reply=reply)


# =============================================================================
# SECTION 7 — MANUAL UI ROUTES
#
# These endpoints power the traditional e-commerce UI flows — registration
# and add-to-cart — without going through the AI agent. They reuse the same
# psycopg3 connection opened during lifespan (app_state.conn) and mirror the
# exact SQL logic used by the create_user_account and add_to_cart tools.
#
# Both routes return a uniform JSON envelope:
#   { "success": bool, "message": str }
# so the frontend can handle both success and error states identically.
# =============================================================================

class RegisterRequest(BaseModel):
    """Payload for the manual registration form."""
    name:         str
    phone_number: str   # Expected in E.164 format, e.g. '+919810001001'
    email:        str   # Stored as-is; add validation on the frontend
    address:      str   # Free-text shipping address


class AddToCartRequest(BaseModel):
    """Payload for the manual add-to-cart action."""
    phone_number: str   # E.164 phone of the logged-in customer
    product_id:   str   # TBS_XXX format ID from the product catalogue
    quantity:     int   # Number of units to add (must be >= 1)


class LoginRequest(BaseModel):
    """Payload for the email-based login endpoint."""
    email: str          # Customer's registered email address


@app.post("/api/login", tags=["manual-ui"])
async def login_user(request: LoginRequest):
    """
    Authenticate a customer by email address.

    Queries public.customers for the provided email using a case-insensitive
    ILIKE match so 'User@Example.com' and 'user@example.com' both resolve to
    the same account. Returns the customer's phone_number and name so the
    frontend can establish a session. Returns 404 if no account matches.
    """
    conn = app_state.conn
    if conn is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")

    try:
        # FIX: Use ILIKE for case-insensitive email matching so that users
        # who registered with a capitalised email can still log in regardless
        # of how they type their address on the login form.
        cursor = conn.execute(
            "SELECT phone_number, name FROM public.customers WHERE email ILIKE %s;",
            (request.email,),
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Account not found. Please register.",
            )

        phone_number, name = row
        return {"success": True, "phone_number": phone_number, "name": name}

    except HTTPException:
        raise  # re-raise 404 as-is
    except Exception as exc:
        import traceback
        print(f"❌  [/api/login] Error: {exc}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Login failed due to a server error: {exc}",
        )


@app.post("/api/register", tags=["manual-ui"])
async def register_user(request: RegisterRequest):
    """
    Register a new customer account via the traditional UI form.

    Inserts a new row into public.customers with Standard tier and 0 loyalty
    points. Returns 409 if the phone number is already registered.
    """
    conn = app_state.conn
    if conn is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")

    try:
        # Check for duplicate phone number before inserting
        cursor = conn.execute(
            "SELECT name FROM public.customers WHERE phone_number = %s;",
            (request.phone_number,),
        )
        existing = cursor.fetchone()
        if existing:
            return {
                "success": False,
                "message": (
                    f"An account is already registered for {request.phone_number}. "
                    "Please log in or use a different number."
                ),
            }

        # Insert the new customer — Standard tier, 0 points.
        # NOTE: `address` is accepted in the Pydantic model (so the frontend
        # payload is not broken) but is intentionally NOT inserted here because
        # the public.customers table does not have an `address` column.
        # customer_id is explicitly generated here to satisfy the UUID primary
        # key constraint on public.customers — without it Postgres raises a
        # not-null violation since there is no server-side default on this column.
        new_customer_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO public.customers
                        (customer_id, phone_number, name, email, membership_tier, loyalty_points)
            VALUES      (%s, %s, %s, %s, 'Standard', 0);
            """,
            (new_customer_id, request.phone_number, request.name, request.email),
        )

        return {
            "success": True,
            "message": (
                f"Welcome to The Body Shop, {request.name}! "
                "Your account has been created with Standard membership and 0 loyalty points."
            ),
        }

    except Exception as exc:
        # Log the full psycopg error — including pgcode, pgerror, and the
        # traceback — so the exact Postgres failure is visible in the terminal.
        import traceback
        import psycopg
        print(f"❌  [/api/register] Exception type : {type(exc).__name__}")
        print(f"❌  [/api/register] Exception value: {exc}")
        if isinstance(exc, psycopg.Error):
            print(f"❌  [/api/register] pgcode        : {exc.pgcode}")
            print(f"❌  [/api/register] pgerror       : {exc.pgerror}")
            if hasattr(exc, 'diag'):
                print(f"❌  [/api/register] diag.detail   : {exc.diag.message_detail}")
                print(f"❌  [/api/register] diag.hint     : {exc.diag.message_hint}")
        print("❌  [/api/register] Full traceback:")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed due to a server error: {exc}",
        )


@app.post("/api/add-to-cart", tags=["manual-ui"])
async def manual_add_to_cart(request: AddToCartRequest):
    """
    Add a product to a customer's cart via the traditional UI.

    Mirrors the add_to_cart tool logic: verifies the product exists in
    public.inventory, confirms the customer account exists, then upserts
    into public.shopping_cart (increments quantity if already present).

    IMPORTANT: When stock is exceeded this endpoint returns a 200 OK with
    {"success": false, "message": "Sorry! Only X left in stock."} instead of
    raising an HTTPException. This allows the frontend alert() to display the
    message without hitting a CORS-blocked error response body.
    """
    conn = app_state.conn
    if conn is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")

    if request.quantity < 1:
        return {"success": False, "message": "Quantity must be at least 1."}

    try:
        import uuid as _uuid

        # Resolve product name and price from inventory
        cursor = conn.execute(
            "SELECT name, price FROM public.inventory WHERE product_id = %s;",
            (request.product_id,),
        )
        product_row = cursor.fetchone()
        if not product_row:
            return {
                "success": False,
                "message": (
                    f"Product '{request.product_id}' was not found in the catalogue. "
                    "Please check the product ID and try again."
                ),
            }
        product_name, unit_price = product_row

        # Verify the customer account exists
        cursor = conn.execute(
            "SELECT name FROM public.customers WHERE phone_number = %s;",
            (request.phone_number,),
        )
        customer = cursor.fetchone()
        if not customer:
            return {
                "success": False,
                "message": (
                    f"No account found for {request.phone_number}. "
                    "Please register before adding items to your cart."
                ),
            }
        customer_name = customer[0]

        # ── Inventory lock check ────────────────────────────────────────────
        # Query available stock and current cart quantity; reject softly if
        # adding the requested quantity would exceed what is in stock.
        inv_cursor = conn.execute(
            "SELECT stock_quantity FROM public.inventory WHERE product_id = %s;",
            (request.product_id,),
        )
        inv_row = inv_cursor.fetchone()
        stock_quantity = inv_row[0] if inv_row else 0

        cart_cursor = conn.execute(
            """
            SELECT COALESCE(quantity, 0) FROM public.shopping_cart
            WHERE  phone_number = %s AND product_id = %s;
            """,
            (request.phone_number, request.product_id),
        )
        cart_row = cart_cursor.fetchone()
        current_qty = cart_row[0] if cart_row else 0

        if current_qty + request.quantity > stock_quantity:
            # FIX: Return a 200 OK soft failure instead of raising HTTPException.
            # The frontend reads response.json() on the success path; a 4xx causes
            # fetch() to reject and the error body is never surfaced to alert().
            available = max(0, stock_quantity - current_qty)
            return {
                "success": False,
                "message": (
                    f"Sorry! Only {available} unit(s) of '{product_name}' left in stock."
                    if available > 0
                    else f"Sorry! '{product_name}' is currently out of stock."
                ),
            }

        # Upsert into shopping_cart — increment quantity if already present
        conn.execute(
            """
            INSERT INTO public.shopping_cart
                        (cart_id, phone_number, product_id, quantity, added_at)
            VALUES      (%s, %s, %s, %s, NOW())
            ON CONFLICT (phone_number, product_id)
            DO UPDATE SET quantity = shopping_cart.quantity + EXCLUDED.quantity;
            """,
            (str(_uuid.uuid4()), request.phone_number, request.product_id, request.quantity),
        )

        # Fetch the updated quantity for the confirmation message
        cursor = conn.execute(
            """
            SELECT quantity FROM public.shopping_cart
            WHERE  phone_number = %s AND product_id = %s;
            """,
            (request.phone_number, request.product_id),
        )
        updated_qty = cursor.fetchone()[0]
        subtotal    = unit_price * updated_qty

        return {
            "success": True,
            "message": (
                f"{product_name} added to {customer_name}'s cart. "
                f"Quantity: {updated_qty} × ₹{unit_price:,} = ₹{subtotal:,}."
            ),
        }

    except Exception as exc:
        print(f"❌  [/api/add-to-cart] Error: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Add-to-cart failed due to a server error: {exc}",
        )