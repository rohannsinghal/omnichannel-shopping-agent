# =============================================================================
# agent.py
# The Body Shop — Virtual Skincare Consultant
# Architecture : Plan-and-Execute with Self-Healing Re-Planner Loop
# Framework    : LangGraph (StateGraph) + LangChain Core + Groq
#
# Node Flow:
#   planner ──► executor ──► replanner ──┬──► END  (plan complete)
#                  ▲                     │
#                  └─────────────────────┘  (tasks remain → loop back)
#
# FIXES vs. v1:
#   FIX 1 — Removed create_react_agent (moved to langchain.agents in LangGraph
#            v1.0; also caused a nested StateGraph that triggered recursive
#            LangChain tracer failures and an unbounded Groq call loop).
#   FIX 2 — Executor is now a flat bind_tools + manual TOOL_MAP dispatch:
#            one LLM call → inspect tool_calls → invoke matching function.
#            Zero nested graphs. Atomically one tool per executor invocation.
#   FIX 3 — LangSmith/LangChain tracer disabled via env vars set BEFORE any
#            langchain import, eliminating the PydanticUserError/TracerException
#            flood that was obscuring real output.
#   FIX 4 — Multi-Model strategy to mitigate Groq free-tier 429 rate limits:
#            planner   → llama-3.3-70b-versatile  (heavy reasoning, low volume)
#            executor  → llama-3.3-70b-versatile  (tool dispatch — upgraded from
#                         8b-instant to prevent BadRequestError on complex calls)
#            replanner → llama-3.1-8b-instant      (structured output, high volume)
#   FIX 5 — Re-Planner system prompt hardened with a HYPER-PRECISE OUTCOME
#            REPORTING directive. The model is now explicitly forbidden from
#            collapsing mixed-result plans (e.g. stock found / cart failed) into
#            a single generalised failure statement. Every past_step observation
#            must be reported individually and accurately.
# ============================================================================= 

import os
import json
from typing import List, Tuple, Optional

# ── Suppress LangSmith tracer BEFORE any langchain import ─────────────────────
# LangChain auto-registers a LangChainTracer if LANGSMITH_API_KEY or
# LANGCHAIN_TRACING_V2 is set. When langsmith's RunTree Pydantic model has
# unresolved forward references (common with mismatched package versions) every
# single callback fires a PydanticUserError, producing hundreds of noise lines.
# Setting these to "false" here (before langchain packages are imported) prevents
# the tracer from registering at all. Safe to remove if you want LangSmith traces.
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGCHAIN_TRACING",    "false")

from dotenv import load_dotenv

# ── LangGraph ─────────────────────────────────────────────────────────────────
from langgraph.graph import StateGraph, END

# ── LangChain Core ────────────────────────────────────────────────────────────
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools    import tool

# ── GROQ ─────────────────────────────────────────────────────────
from langchain_groq import ChatGroq
# ── Pydantic ──────────────────────────────────────────────────────────────────
from pydantic import BaseModel, Field

# ── TypedDict for AgentState ──────────────────────────────────────────────────
from typing_extensions import TypedDict

load_dotenv()


# =============================================================================
# SECTION 1 — TOOL IMPORTS
# Import all real tools from their dedicated modules.
# =============================================================================

from tools_skin_master  import consult_skin_master
from tools_catalog      import search_chroma_products
from tools_inventory    import check_sql_inventory
from tools_commerce     import add_to_cart, get_loyalty_profile, checkout_cart, create_user_account, view_cart, remove_from_cart
from tools_store        import find_nearby_stores
from tools_customer_care import get_order_status
from tools_vision       import analyze_uploaded_image

TOOL_LIST = [
    consult_skin_master,
    search_chroma_products,
    check_sql_inventory,
    add_to_cart,
    view_cart,
    remove_from_cart,
    get_loyalty_profile,
    checkout_cart,
    find_nearby_stores,
    get_order_status,
    analyze_uploaded_image,
    create_user_account
]


# =============================================================================
# SECTION 2 — LLM INITIALISATION  (Multi-Model Strategy — Groq Paid Tier)
#
# planner_llm   : openai/gpt-oss-120b — Groq's current flagship 120B production
#                 model (replaced llama-4-maverick Feb 2026). No tools bound.
#                 Used with .with_structured_output() for validated Plan output.
#
# executor_llm  : llama-3.1-8b-instant — lightweight, high-RPM model.
#                 Tools bound via .bind_tools(TOOL_LIST). Manual TOOL_MAP
#                 dispatch in executor_node — no nested graph.
#
# replanner_llm : openai/gpt-oss-120b — same heavyweight brain as the planner.
#                 On the paid tier RPM is not a bottleneck, so we use the
#                 stronger model here too for higher-quality self-healing.
#                 Used with .with_structured_output(ReplannerOutput).
# =============================================================================

_GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ── Planner Brain: 120B for deep multi-step reasoning ────────────────────────
planner_llm = ChatGroq(
    model       = "openai/gpt-oss-120b",
    temperature = 0,
    api_key     = _GROQ_API_KEY,
)

# ── Executor Muscle: 70B for reliable tool-call dispatch ─────────────────────
executor_llm = ChatGroq(
    model       = "llama-3.3-70b-versatile",
    temperature = 0,
    api_key     = _GROQ_API_KEY,
).bind_tools(TOOL_LIST)

# ── Bare executor for conversational (non-tool) tasks ─────────────────────────
executor_llm_bare = ChatGroq(
    model       = "llama-3.3-70b-versatile",
    temperature = 0,
    api_key     = _GROQ_API_KEY
)   # No .bind_tools() — used when the task is purely conversational

# ── Replanner Brain: 120B for structured self-healing decisions ───────────────
replanner_llm = ChatGroq(
    model       = "openai/gpt-oss-120b",
    temperature = 0,
    api_key     = _GROQ_API_KEY,
)

# =============================================================================
# SECTION 3 — STATE DEFINITION
#
# AgentState is the single shared object threaded through every graph node.
# LangGraph reads the TypedDict fields and merges updates returned by nodes.
#
# Fields:
#   messages   — full conversation history (HumanMessage / AIMessage objects)
#   plan       — ordered list of task strings still to be executed
#   past_steps — completed steps as (task_string, observation_string) tuples
#   response   — final natural-language answer; non-empty signals plan complete
# =============================================================================

class AgentState(TypedDict):
    messages     : List
    plan         : List[str]
    past_steps   : List[Tuple[str, str]]
    response     : Optional[str]
    phone_number : Optional[str]   # FIX 2: session phone threaded through state
                                   # so planner always has the right number and
                                   # never hallucinates one from tool docstrings.


# =============================================================================
# SECTION 4 — PYDANTIC PLAN MODEL
#
# Using Pydantic as the structured output schema gives us a typed, validated
# List[str] — never a raw JSON blob — with automatic retry/repair from the LLM.
# =============================================================================

class Plan(BaseModel):
    """Ordered list of single-action tasks produced by the planner."""
    tasks: List[str] = Field(
        description=(
            "Ordered list of single-action tasks to complete the user's request. "
            "Each task must reference exactly one tool or one user-facing action."
        )
    )


# =============================================================================
# SECTION 5 — PLANNER NODE
#
# Reads the latest HumanMessage and produces a validated Plan via
# with_structured_output. The system prompt enforces:
#   • Hard routing rules  (which tool handles which intent)
#   • Transaction sequencing constraint (search -> stock -> cart)
#   • Three annotated few-shot examples covering all boundary cases
# =============================================================================

PLANNER_SYSTEM_PROMPT = """
You are the Planning Intelligence for The Body Shop's AI Skincare Consultant.
Your ONLY job is to decompose the user's message into an ordered list of
single-action tasks. You do NOT answer the user directly. You do NOT call tools.
You output ONLY a structured Plan.

════════════════════════════════════════════════════════════════
AVAILABLE TOOLS (use these exact names in your tasks)
════════════════════════════════════════════════════════════════
- consult_skin_master      — ALL medical/skincare advice: skin conditions,
                             ingredient safety, routine building, treatment
                             guidance. ONLY for dermatological questions.
- search_chroma_products   — Semantic product catalog search by concern,
                             ingredient, skin type, or product name.
- check_sql_inventory      — Real-time stock check for a specific product_id
                             returned by search_chroma_products.
- add_to_cart              — Adds a verified product to the customer's
                             persistent cloud cart. Requires phone_number
                             AND product_id. Only call after inventory check.
- view_cart                — Retrieves the full contents of the customer's
                             cart, including item names, quantities, prices,
                             and the timestamp each item was added. Use this
                             whenever the user asks to see or check their cart.
- remove_from_cart         — Removes a specific product from the customer's
                             cart by product_id. Requires phone_number AND
                             product_id. Only call when the user explicitly
                             asks to remove an item. Always confirm removal.
- get_loyalty_profile      — Retrieves a customer's membership tier and
                             loyalty point balance by phone number.
- checkout_cart            — Generates an itemised order summary with loyalty
                             discount applied and a Stripe payment link.
                             Requires phone_number.
- find_nearby_stores       — Locates nearest Body Shop retail stores by GPS
                             coordinates OR city/neighbourhood text.
- get_order_status         — Retrieves shipping/delivery status for an order.
                             Requires an order ID in format TBS-XXXX.
- analyze_uploaded_image   — Runs a PyTorch vision model on a user-uploaded
                             photo to detect skin type. MUST be called before
                             any image-based product recommendations.

════════════════════════════════════════════════════════════════
HARD ROUTING RULES  (never violate these)
════════════════════════════════════════════════════════════════
RULE 1 — MEDICAL / SKINCARE ADVICE:
  Any question about skin reactions, ingredient safety, conditions, or routine
  building ALWAYS starts with consult_skin_master. Never skip this step.
  NEVER route store locations, order status, or account questions to
  consult_skin_master — it is strictly for dermatological queries only.

RULE 2 — TRANSACTION SEQUENCING:
  Adding a product to the cart MUST follow this exact order:
    search_chroma_products → check_sql_inventory → add_to_cart
  Never call add_to_cart without a preceding inventory check.
  Never call check_sql_inventory without a preceding catalog search.

RULE 3 — COMBINED MEDICAL + TRANSACTION:
  When the user has a skin concern AND wants to buy, consult_skin_master
  goes FIRST to shape the search query, then the full RULE 2 sequence follows.

RULE 4 — STORE LOCATIONS:
  ALWAYS use find_nearby_stores for any store/branch location request.
  Use GPS mode (user_lat, user_lon) if coordinates are available,
  otherwise use text mode (location_query).

RULE 5 — ACCOUNT & LOYALTY:
  • Loyalty points / tier queries → get_loyalty_profile (requires phone number)
  • Checkout / payment           → checkout_cart (requires phone number)
  • Order tracking / status      → get_order_status (requires TBS-XXXX order ID)
  NEVER use consult_skin_master for any of these.

RULE 6 — IMAGE UPLOADS:
  If the user has uploaded an image or selfie, ALWAYS call
  analyze_uploaded_image FIRST with the file path before any product
  recommendations. Never describe or interpret an image without this tool.

RULE 7 — INTENT GATE FOR CART ACTIONS:
  NEVER call add_to_cart unless the user has EXPLICITLY said one of:
  "add to cart", "add it", "I'll take it", "buy this", "purchase this",
  "place order", or given an equally unambiguous purchase command.
  Browsing language ("I want to buy a gift", "looking for a product",
  "recommend something") means SEARCH and RECOMMEND only.
  The correct plan for browsing: consult_skin_master → search_chroma_products
  → check_sql_inventory → Respond to user with recommendations.
  Stop there. Do NOT add to cart without explicit instruction.

RULE 8 — CART VIEWING:
  If the user asks to "see my cart", "view cart", "what's in my cart", or
  any equivalent phrasing, ALWAYS use view_cart (requires phone_number).
  Do NOT call any other tool first. Do NOT hallucinate cart contents.

RULE 9 — CART REMOVAL:
  If the user asks to "remove", "delete", or "take out" an item from their
  cart, ALWAYS use remove_from_cart (requires phone_number AND product_id).
  If the product_id is unknown, call view_cart first to retrieve it, then
  call remove_from_cart. Always confirm the removal to the user.
  NEVER hallucinate a confirmation if the tool has not been called yet.

RULE 10 — TOOL FAILURE HANDLING:
  If any tool returns a TOOL_ERROR or an empty/unexpected result, NEVER
  fabricate a greeting or positive response. Report the exact failure
  to the user and suggest a corrective action (e.g. check phone number,
  try a different product name). NEVER hallucinate greetings if a tool fails.

════════════════════════════════════════════════════════════════
FEW-SHOT EXAMPLES
════════════════════════════════════════════════════════════════

EXAMPLE 1 — Pure medical advice
User: "My face burns from retinol. What should I do?"
Plan tasks:
  - "Call consult_skin_master with query='retinol burn face irritation treatment'"
  - "Respond to the user with the advice"

EXAMPLE 2 — Direct purchase
User: "Add the Vitamin C serum to my cart. My number is +919810001001."
Plan tasks:
  - "Call search_chroma_products with query='Vitamin C serum' to retrieve product_id"
  - "Call check_sql_inventory with the product_id from step 1"
  - "Call add_to_cart with phone_number='+919810001001' and product_id from step 1"
  - "Confirm the cart addition to the user"

EXAMPLE 3 — Skin condition + purchase
User: "I have fungal acne. Add a safe cleanser to my cart. My number is +919810001001."
Plan tasks:
  - "Call consult_skin_master with query='fungal acne safe cleanser ingredients to avoid'"
  - "Call search_chroma_products using ingredient constraints from step 1"
  - "Call check_sql_inventory with the product_id from step 2"
  - "Call add_to_cart with phone_number='+919810001001' and product_id from step 3"
  - "Confirm addition and summarise the advice to the user"

EXAMPLE 4 — Store location + loyalty points
User: "Where's the nearest store to Cyber Hub? Also check my points for +919810001001."
Plan tasks:
  - "Call find_nearby_stores with location_query='Cyber Hub, Gurgaon'"
  - "Call get_loyalty_profile with phone_number='+919810001001'"
  - "Respond to the user with the store address and loyalty balance"

EXAMPLE 5 — Order tracking
User: "Where is my order TBS-9901?"
Plan tasks:
  - "Call get_order_status with order_id='TBS-9901'"
  - "Relay the order status and tracking details to the user"

EXAMPLE 6 — Image upload
User: "Here's my selfie. What products should I use?" [image uploaded]
Plan tasks:
  - "Call analyze_uploaded_image with the uploaded file path"
  - "Call search_chroma_products using the detected skin type from step 1"
  - "Recommend the products to the user based on their skin profile"

EXAMPLE 7 — Checkout
User: "I'm ready to pay. My number is +919810001001."
Plan tasks:
  - "Call checkout_cart with phone_number='+919810001001'"
  - "Share the payment link and order summary with the user"

EXAMPLE 8 — View cart
User: "Show me what's in my cart. My number is +919810001001."
Plan tasks:
  - "Call view_cart with phone_number='+919810001001'"
  - "Present the cart contents and totals to the user"

EXAMPLE 9 — Remove item from cart (product_id known)
User: "Remove TBS_029 from my cart. My number is +919810001001."
Plan tasks:
  - "Call remove_from_cart with phone_number='+919810001001' and product_id='TBS_029'"
  - "Confirm the removal to the user"

EXAMPLE 10 — Remove item from cart (product_id unknown)
User: "Remove the serum from my cart. My number is +919810001001."
Plan tasks:
  - "Call view_cart with phone_number='+919810001001' to identify the serum's product_id"
  - "Call remove_from_cart with phone_number='+919810001001' and the product_id from step 1"
  - "Confirm the removal to the user"

════════════════════════════════════════════════════════════════
OUTPUT FORMAT
════════════════════════════════════════════════════════════════
Return only a Plan with a `tasks` list. Maximum 6 tasks.
Include all relevant context (product names, phone numbers, order IDs,
skin conditions, file paths) inside each task string so the executor
has full information without needing to re-read prior steps.

════════════════════════════════════════════════════════════════
CRITICAL — CHITCHAT & GREETINGS RULE (STRICTLY ENFORCED)
════════════════════════════════════════════════════════════════
DO NOT create plans for simple chitchat or greetings. If the user says
hello, hi, how are you, thanks, bye, or any other simple social phrase,
your plan should consist of exactly ONE task: "Directly respond to the user."
DO NOT overcomplicate greetings. DO NOT call any tools for chitchat.
DO NOT create multi-step plans for messages that require no tool use.

STRICT SMALL-TALK RULE:
If the user is just saying hello, asking how you are, or making small talk,
DO NOT generate a plan with multiple steps. Output a single step:
"Converse with the user."
""".strip()


def planner_node(state: AgentState) -> dict:
    """
    Planner node — produces the initial execution Plan.

    Extracts the most recent HumanMessage, invokes the planner LLM with
    structured output (Pydantic Plan), prints the plan for debugging, and
    writes the task list into state.

    State reads  : messages, phone_number
    State writes : plan
    """
    user_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break

    # FIX 2: Build a session-aware system prompt that injects the customer's
    # phone number. This prevents the executor LLM from hallucinating a number
    # it has seen in tool docstrings (e.g. the +919810001001 test fixture).
    session_phone = state.get("phone_number") or "unknown — ask the user"
    session_context = (
        f"\n\nSESSION CONTEXT (injected by the system — treat as ground truth):\n"
        f"  Customer Phone Number: {session_phone}\n"
        "  Always use this exact phone number in any task that requires "
        "phone_number. Never substitute a different number."
    )
    planner_prompt_with_context = PLANNER_SYSTEM_PROMPT + session_context

    print("\n  🧠  [PLANNER] Analysing request and generating plan...")

    structured_planner = planner_llm.with_structured_output(Plan)
    plan_obj: Plan = structured_planner.invoke([
        SystemMessage(content=planner_prompt_with_context),
        HumanMessage(content=user_message),
    ])

    # ── Print plan to console BEFORE execution so you can debug reasoning ────
    print("\n  📋  [PLAN GENERATED] ─────────────────────────────────────")
    for i, task in enumerate(plan_obj.tasks, 1):
        print(f"       Step {i}: {task}")
    print("  ──────────────────────────────────────────────────────────\n")

    return {"plan": plan_obj.tasks}


# =============================================================================
# SECTION 6 — EXECUTOR NODE  (flat bind_tools + manual dispatch)
#
# WHY NOT create_react_agent:
#   In LangGraph >= v1.0, create_react_agent moved to langchain.agents and
#   compiles its own inner StateGraph. Nesting that inside our outer node:
#     1. Triggers recursive LangChain tracer callbacks -> hundreds of
#        PydanticUserError / TracerException lines flood the console.
#     2. The inner loop's termination is prompt-driven; Llama-3.3-70b ignores
#        "call ONE tool only" on multi-step tasks -> unbounded Groq API calls.
#
# THE FIX — three flat steps, no nested graph:
#   Step A: One LLM call (executor_llm has tools bound) -> AIMessage may contain
#           a tool_calls list with name + args payloads.
#   Step B: If tool_calls present, dispatch ONLY the first via TOOL_MAP.
#           Ignoring any additional calls enforces the one-tool-per-step contract
#           at the *code* level, not the prompt level — immune to LLM drift.
#   Step C: Record raw tool output as the observation string.
#
# The outer StateGraph loop already visits the executor once per task, so we
# never need an inner retry loop. Result: deterministic, one API call per step.
# =============================================================================

# Fast name -> callable lookup. Keys must match the @tool function names exactly.
TOOL_MAP = {t.name: t for t in TOOL_LIST}

EXECUTOR_SYSTEM_PROMPT = SystemMessage(content=(
    "You are a precise tool-execution agent for The Body Shop's skincare consultant. "
    "You will receive a single task description. "
    "Identify the single best tool for that task and call it with the correct arguments. "
    "Extract all argument values directly from the task description. "
    "Call ONLY ONE tool. Do not add commentary before the tool call."
))

_CONVERSATIONAL_SIGNALS = (
    "apologise", "apologi", "inform the user", "respond to the user",
    "confirm", "relay", "tell the user", "share the", "summarise",
    "ask the user",
)

def _is_conversational_task(task: str) -> bool:
    """Return True when the task is purely conversational (no tool required)."""
    low = task.lower()
    return any(sig in low for sig in _CONVERSATIONAL_SIGNALS)

def _dispatch_tool(tool_call: dict) -> str:
    """
    Executes a single tool_call payload produced by ChatGroq.

    Args:
        tool_call: {"name": str, "args": dict, "id": str}

    Returns:
        Tool output as a string, or a TOOL_ERROR string on any failure.
    """
    name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    if name not in TOOL_MAP:
        return (
            f"TOOL_ERROR: Unknown tool '{name}'. "
            f"Available: {list(TOOL_MAP.keys())}"
        )

    try:
        # LangChain @tool.invoke() accepts a dict of kwargs matching the signature
        result = TOOL_MAP[name].invoke(args)
        return str(result)
    except Exception as exc:
        return f"TOOL_ERROR: {name} raised {type(exc).__name__}: {exc}"


def executor_node(state: AgentState) -> dict:
    """
    Executor node — runs the next pending task with exactly one tool call.

    Flow:
      1. Pop plan[0] as current_task; remaining tasks stay in plan.
      2. Send current_task to executor_llm (tools bound) -> AIMessage.
      3. If AIMessage.tool_calls present -> dispatch the FIRST call via TOOL_MAP.
         Additional calls are intentionally ignored (one-tool-per-step contract
         enforced at code level, not prompt level).
      4. If no tool_calls -> use AIMessage.content as observation (handles
         "Respond to user" or "Confirm with user" steps gracefully).
      5. Append (current_task, observation) to past_steps.

    State reads  : plan, past_steps
    State writes : plan (first task removed), past_steps (new entry appended)
    """
    if not state.get("plan"):
        return {"past_steps": [("No task", "No plan provided")]}

    current_plan = state["plan"]
    if not current_plan:
        return {}   # guard: replanner handles the empty-plan case

    current_task   = current_plan[0]
    remaining_plan = current_plan[1:]

    # ── Build a readable past-steps context string ─────────────────────────────
    # This is the fix for cross-step hallucination: when a task says "use the
    # product_id from step 2", the executor now has the full observation history
    # to resolve that reference accurately instead of guessing.
    past_steps_list = state.get("past_steps", [])
    if past_steps_list:
        past_steps_context = "PREVIOUS STEPS CONTEXT (use these results to fill in any arguments):\n" + "\n".join(
            f"  Step {i+1}:\n    Task       : {task}\n    Observation: {obs}"
            for i, (task, obs) in enumerate(past_steps_list)
        ) + "\n\n"
    else:
        past_steps_context = ""

    print(f"\n  ⚡  [EXECUTOR] Task: '{current_task[:80]}{'...' if len(current_task) > 80 else ''}'")

    try:
        if _is_conversational_task(current_task):
            # ── Conversational step: use bare LLM (no tools bound) ─────────
            # Include full conversation history so the executor knows what the
            # user actually said — prevents generic greetings and hallucinations.
            messages = [
                SystemMessage(content=(
                    "You are a warm, expert Body Shop skincare consultant. "
                    "Write a single, concise reply to the user based on the task below. "
                    "Do NOT call any tools. Output plain text only."
                ))
            ] + state["messages"] + [
                HumanMessage(content=f"{past_steps_context}Task: {current_task}"),
            ]
            ai_msg: AIMessage = executor_llm_bare.invoke(messages)
            observation = ai_msg.content or "(No response generated.)"

        else:
            # ── Tool step: use tool-bound LLM ──────────────────────────────
            # FIX (Chatbot Amnesia): messages = [SystemMessage] + state["messages"]
            # + [HumanMessage(task)] so the executor sees the full conversation
            # history and can resolve references like "my phone number" without
            # hallucinating values it has never seen in the current task string.
            _exec_system_prompt = (
                "You are a precise tool-execution agent for The Body Shop's skincare consultant. "
                "You will receive a single task description. "
                "Identify the single best tool for that task and call it with the correct arguments. "
                "Extract all argument values from the task description or the conversation history above. "
                "Call ONLY ONE tool. Do not add commentary before the tool call."
            )
            messages = (
                [SystemMessage(content=_exec_system_prompt)]
                + state["messages"]
                + [HumanMessage(content=f"{past_steps_context}CURRENT TASK:\n{current_task}")]
            )
            ai_msg: AIMessage = executor_llm.invoke(messages)

            if ai_msg.tool_calls:
                first_call = ai_msg.tool_calls[0]
                args_preview = str(first_call["args"])
                print(
                    f"  🔧  [{first_call['name']}] "
                    f"args: {args_preview[:100]}"
                    f"{'...' if len(args_preview) > 100 else ''}"
                )
                observation = _dispatch_tool(first_call)
            else:
                observation = ai_msg.content or "(No tool called and no text produced.)"

    except Exception as exc:
        observation = f"TOOL_ERROR: executor_node raised {type(exc).__name__}: {exc}"

    print(f"  🔍  [OBS] {observation[:160]}{'...' if len(observation) > 160 else ''}\n")

    return {
        "plan"       : remaining_plan,
        "past_steps" : state.get("past_steps", []) + [(current_task, observation)],
    }


# =============================================================================
# SECTION 7 — RE-PLANNER NODE  (Self-Healing)
#
# Reads execution history (past_steps) and remaining plan. Makes one of three
# decisions:
#
#   A) PLAN COMPLETE — no tasks remain and no critical failure detected.
#      Synthesises a warm, expert final response. Sets state["response"].
#
#   B) PLAN NEEDS REPAIR — failure signal detected in past_steps observations
#      (NO_RESULTS, OUT_OF_STOCK, TOOL_ERROR).
#      Surgically replaces broken downstream tasks with recovery tasks.
#
#   C) TASKS REMAIN — no failures, tasks still pending.
#      Returns remaining tasks unchanged; executor continues.
#
# Uses with_structured_output(ReplannerOutput) for typed, validated decisions.
# =============================================================================

REPLANNER_SYSTEM_PROMPT = """
You are the Re-Planning Intelligence for The Body Shop's AI Skincare Consultant.
You review what has been completed and decide what happens next.

You receive:
  • ORIGINAL USER MESSAGE — the request we are fulfilling
  • PAST STEPS            — log of (task, observation) pairs already executed
  • REMAINING PLAN        — tasks still queued

════════════════════════════════════════════════════════════════
DECISION LOGIC
════════════════════════════════════════════════════════════════

CASE 1 — PLAN COMPLETE
  Trigger: remaining_plan is empty AND no unresolved failures in past_steps.
  Action : Set `response` to a warm, expert final answer synthesising all
           observations. Follow ALL formatting and anti-hallucination rules
           below. Leave `tasks` empty.

CASE 2 — STEP FAILED (self-heal)
  Trigger: An observation contains "NO_RESULTS", "OUT_OF_STOCK", "TOOL_ERROR",
           or "Error: Catalog search is temporarily down".
  Action : Identify which downstream tasks are now invalid and replace them:
    "NO_RESULTS"      -> "Inform the user no matching product was found and ask
                          them to describe a different product."
    "OUT_OF_STOCK"    -> "Inform the user the product is out of stock and offer
                          to search for an alternative."
    "TOOL_ERROR"      -> "Politely tell the user you are having technical
                          difficulties and ask them to try again shortly."
    "temporarily down"-> "Politely tell the user you are having technical
                          difficulties and ask them to try again shortly."
     IMPORTANT: Once you have generated ONE apology/recovery task and it has
  been executed successfully (observation is non-empty text, not a TOOL_ERROR),
  treat the plan as COMPLETE. Set `response` to the apology text from that
  observation. Do NOT generate another recovery task.
  Update `tasks` with the repaired remaining plan. Leave `response` empty.

CASE 3 — TASKS REMAIN
  Trigger: remaining_plan still has items and no failures detected.
  Action : Return remaining tasks unchanged in `tasks`. Leave `response` empty.

════════════════════════════════════════════════════════════════
CRITICAL — RESPONSE FORMATTING (NON-NEGOTIABLE)
════════════════════════════════════════════════════════════════
When writing the final `response`, you are speaking directly to the customer
as a fun, Gen-Z/Millennial beauty expert. You MUST follow every rule below.

RULE F1 — NO WALLS OF TEXT:
  Your response must be at most 3–4 short sentences of prose, followed by
  bullet points only when you are listing one or more products.

RULE F2 — FUN & PUNCHY VOICE:
  Use emojis naturally (✨, 🌿, 🧴, 💚). Be warm, enthusiastic, and concise.
  Write in British English.

RULE F3 — NEVER EXPOSE INTERNALS:
  NEVER say "Step 1", "Step 2", "Task", "search", "inventory", "database",
  "tool", "observation", "plan", "executor", "I ran", "I called", or ANY word
  that reveals your internal process. The user does not care how you got the
  information — just give it to them seamlessly.

RULE F3a — ZERO ROBOTIC LANGUAGE (STRICTLY ENFORCED):
  ❌ FORBIDDEN phrases — instant failure if any of these appear in `response`:
     "Step 1", "Step 2", "Step 3", "Task 1", "Task 2", "Task completed",
     "I have completed", "I have executed", "I have performed",
     "I searched for", "I queried", "I called a tool", "I ran a tool",
     "I used the", "the tool returned", "the plan was", "the executor",
     "I summarised", "I retrieved", "based on the steps",
     "based on the observations", "the observations show".
  If a tool fails: say "I'm having a few technical difficulties right now 🙏
  — could you try again in a moment?" NEVER describe which tool failed or why.
  If the user asks for a product: list it directly. No preamble about how you
  found it. No mention of searching, databases, or inventory systems.

RULE F4 — MANDATORY BULLET FORMAT FOR PRODUCTS:
  When listing any product (even a single product), you MUST use this exact
  markdown format for each item — no exceptions:

  • **[Product Name] (₹[Price]):** [One sentence on what it does and why it
    helps the customer's specific concern.] [Relevant emoji]

  After the bullet list, end with exactly ONE short, punchy call-to-action
  sentence (e.g. "Want me to pop one into your bag? 🛍️").
  NEVER write a paragraph description when a bullet list is required.

RULE F5 — NO HOLLOW OPENERS:
  NEVER open with "Certainly!", "Of course!", "Absolutely!", "Great news!",
  or any hollow affirmation filler. Lead with substance.

RULE F6 — MIXED RESULTS — REPORT EACH OUTCOME SEPARATELY:
  NEVER collapse multiple outcomes into one vague statement.
  NEVER let a failed step taint a step that succeeded.
  If stock was confirmed but cart failed, state both facts individually.
    WRONG: "I was unable to complete your request due to an error."
    RIGHT: "The Vitamin C Glow Serum is fully in stock ✨ — I just couldn't add
            it to your cart because I couldn't find an account for that number.
            Could you double-check your phone number, or shall I help you
            register? Once that's sorted I'll add it straight away. 💚"

════════════════════════════════════════════════════════════════
CRITICAL — ANTI-HALLUCINATION INVENTORY RULE (STRICTLY ENFORCED)
════════════════════════════════════════════════════════════════
You are FORBIDDEN from making any claim about a product's stock status unless
`check_sql_inventory` has been explicitly run for that product in past_steps.

RULE I1 — PRODUCT FOUND, INVENTORY NOT YET CHECKED:
  If `search_chroma_products` returned a product but `check_sql_inventory`
  has NOT been run for it yet, you MUST include the phrase:
  "I can check the stock for this if you like."
  You are FORBIDDEN from saying the product is in stock, available, or
  ready to add to cart. You are equally FORBIDDEN from saying it is out of
  stock. State only that the product exists in the catalogue, then offer
  to check availability.

RULE I2 — OUT OF STOCK CLAIM:
  You are FORBIDDEN from claiming a product is out of stock unless
  `check_sql_inventory` explicitly returned 0 for that product_id in
  past_steps. Zero inference. Zero assumption. Only report what the tool
  returned.

RULE I3 — GENERAL ANTI-HALLUCINATION:
  Every factual claim in your `response` (product name, price, stock level,
  loyalty points, store address, order status) MUST be directly traceable to
  a specific observation in past_steps. Do not infer, assume, or fabricate
  any outcome that is not explicitly stated in the observation text.

════════════════════════════════════════════════════════════════
EXAMPLE — CORRECT PRODUCT LISTING (CASE 1, products in stock)
════════════════════════════════════════════════════════════════
"Oily skin struggles are real, but we've totally got you covered! 🌿 Here's
what's in stock and perfect for your skin type:

• **Tea Tree Skin Clearing Facial Wash (₹895):** A cult-favourite antibacterial
  cleanser that tackles excess oil and calms active breakouts. 🌱
• **Drops of Youth™ Concentrate (₹2,495):** A lightweight serum packed with
  plant stem cells to keep your skin balanced and bouncy all day. ✨

Want me to pop either of these into your bag? 🛍️"

════════════════════════════════════════════════════════════════
EXAMPLE — CORRECT TECHNICAL FAILURE RESPONSE
════════════════════════════════════════════════════════════════
  WRONG: "I attempted to search the catalog tool but it returned an error."
  RIGHT: "I'm having a few technical difficulties right now 🙏 — could you
          try again in a moment? I want to make sure I get you the right picks!"

════════════════════════════════════════════════════════════════
OUTPUT FORMAT
════════════════════════════════════════════════════════════════
Return a ReplannerOutput with:
  tasks    : list[str]  — updated remaining tasks (empty if plan is done)
  response : str        — final user-facing answer (empty string if not done)

════════════════════════════════════════════════════════════════
⚠️  CRITICAL — YOU ARE THE FINAL VOICE THE CUSTOMER HEARS ⚠️
════════════════════════════════════════════════════════════════
NEVER summarise your internal steps in the final response.
NEVER say "Step 1 succeeded", "Step 2 failed", "I searched for", "I called a tool",
"I responded with", "the plan was", "the executor", or any phrase that reveals
your internal reasoning process.

You are the final customer-facing voice. NEVER say "Step 1", "Task", or
"Task completed". Just give the natural, conversational answer based on the
observations. Speak directly as a beauty consultant, not as a system narrating
its own actions.

If the past steps show you simply greeted the user or answered a chitchat message,
output the greeting or reply DIRECTLY as the response — do not narrate it.
  WRONG: "I responded to the user with a greeting."
  RIGHT: "Hi there! 👋 How can I help you today? 🌿"

The customer sees ONLY your `response` field. Make it warm, natural, and human.
Write as if you are a real beauty consultant — not a robot describing its own actions.

════════════════════════════════════════════════════════════════
STRICTLY BANNED — ROBOTIC SUMMARISATION PHRASES (ZERO TOLERANCE)
════════════════════════════════════════════════════════════════
You are ABSOLUTELY FORBIDDEN from using ANY of the following patterns
in your `response` field. Violation = automatic failure.

  ❌ NEVER summarise what tools you ran: "I searched for...", "I checked
     the inventory...", "I called the cart tool..."
  ❌ NEVER use numbered steps: "Step 1:", "Step 2:", "Task 1:", "Task 2:"
  ❌ NEVER announce completion: "Task completed.", "I have completed the
     steps.", "All tasks have been executed.", "Done!"
  ❌ NEVER narrate observations: "Based on the observations...", "The tool
     returned...", "According to the past steps..."
  ❌ NEVER write a preamble before the actual answer: "I have now gathered
     all the information you need. Here is what I found:"

INSTEAD — just converse naturally based on the data:
  ✅ Lead directly with the useful information or recommendation.
  ✅ Speak as a beauty consultant who simply KNOWS the answer.
  ✅ Use the bullet format from RULE F4 when listing products.
  ✅ Keep it punchy: 1–4 sentences of prose max, then bullets if needed.
""".strip()


class ReplannerOutput(BaseModel):
    """Structured output from the re-planner."""
    tasks   : List[str] = Field(
        default_factory=list,
        description="Remaining tasks to execute. Empty when plan is complete.",
    )
    response: str = Field(
        default="",
        description=(
            "Final user-facing response. Non-empty only when the plan is fully "
            "resolved (success or graceful failure with user guidance)."
        ),
    )


def replanner_node(state: AgentState) -> dict:
    """
    Re-planner node — evaluates execution history, heals or concludes the plan.

    State reads  : messages, plan, past_steps
    State writes : plan (possibly repaired), response (if plan complete)
    """
    past_steps_text = "\n".join(
        f"  Step {i+1}:\n    Task       : {task}\n    Observation: {obs}"
        for i, (task, obs) in enumerate(state.get("past_steps", []))
    ) or "  (none yet)"

    remaining_text = "\n".join(
        f"  {i+1}. {task}"
        for i, task in enumerate(state.get("plan", []))
    ) or "  (none — plan may be complete)"

    original_request = ""
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            original_request = msg.content
            break

    replanner_input = (
        f"ORIGINAL USER MESSAGE:\n  {original_request}\n\n"
        f"FULL CONVERSATION HISTORY:\n"
        + "\n".join(
            f"  {'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in state.get("messages", [])
            if hasattr(m, "content") and m.content
        )
        + f"\n\nPAST STEPS:\n{past_steps_text}\n\n"
        f"REMAINING PLAN:\n{remaining_text}"
    )

    print("  🔄  [REPLANNER] Evaluating execution state...")

    structured_replanner = replanner_llm.with_structured_output(ReplannerOutput)
    output: ReplannerOutput = structured_replanner.invoke([
        SystemMessage(content=REPLANNER_SYSTEM_PROMPT),
        HumanMessage(content=replanner_input),
    ])

    if output.response:
        print("  ✅  [REPLANNER] Plan complete — generating final response.\n")
    elif output.tasks != state.get("plan", []):
        print(f"  🩹  [REPLANNER] Plan repaired — {len(output.tasks)} task(s) remain.")
        for i, t in enumerate(output.tasks, 1):
            print(f"       Revised Step {i}: {t}")
        print()
    else:
        print(f"  ▶️   [REPLANNER] Continuing — {len(output.tasks)} task(s) remain.\n")

    return {
        "plan"    : output.tasks,
        "response": output.response if output.response else state.get("response", ""),
    }


# =============================================================================
# SECTION 8 — CONDITIONAL ROUTING
#
# Single decision point after every re-planner invocation:
#   non-empty response -> END       (plan closed, surface answer to user)
#   non-empty plan     -> executor  (keep executing remaining tasks)
#   both empty         -> END       (safe fallback, shouldn't occur normally)
# =============================================================================

# Maximum executor cycles per user turn — hard stop against infinite loops
_MAX_STEPS = 6

def should_continue(state: AgentState) -> str:
    if state.get("response"):
        return "end"
    if state.get("plan") and len(state.get("past_steps", [])) < _MAX_STEPS:
        return "executor"
    return "end"


# =============================================================================
# SECTION 9 — GRAPH CONSTRUCTION
#
# Topology:
#   START -> planner -> executor -> replanner --+-- END
#                          ^                   |
#                          +-------------------+
# =============================================================================

def build_graph(memory=None) -> StateGraph:
    """Assembles and compiles the Plan-and-Execute StateGraph."""
    builder = StateGraph(AgentState)

    builder.add_node("planner",   planner_node)
    builder.add_node("executor",  executor_node)
    builder.add_node("replanner", replanner_node)

    builder.set_entry_point("planner")
    builder.add_edge("planner",  "executor")
    builder.add_edge("executor", "replanner")
    builder.add_conditional_edges(
        "replanner",
        should_continue,
        {"executor": "executor", "end": END},
    )

    return builder.compile(checkpointer=memory)


# =============================================================================
# SECTION 10 — TERMINAL CHAT LOOP  (Postgres-backed persistent memory)
#
# Architecture:
#   • PostgresSaver.from_conn_string() — LangGraph native checkpointer that
#     manages its own connection to Supabase via psycopg3. Persists the full
#     graph state (messages, plan, past_steps) after every node execution.
#   • memory.setup()  — idempotent bootstrap; auto-creates the three internal
#     checkpoint tables on first run, no manual SQL migrations needed:
#         checkpoints / checkpoint_blobs / checkpoint_writes
#   • thread_id — keyed on the customer's phone number so every session is
#     fully resumable across process restarts.
# =============================================================================

if __name__ == "__main__":

    from langgraph.checkpoint.postgres import PostgresSaver

    DIVIDER    = "─" * 62
    BOT_PREFIX = "\n  🌿  Body Shop Consultant:\n"

    POSTGRES_URI = os.getenv("POSTGRES_URI")
    if not POSTGRES_URI:
        raise RuntimeError(
            "POSTGRES_URI is not set. Add it to your .env file before starting."
        )

    # ── FIX 1: psycopg3 prepared-statement crash with Supabase pooler ─────────
    # Supabase's pgbouncer pooler (port 6543) does not support server-side
    # prepared statements. PostgresSaver uses psycopg3 internally, so every
    # checkpoint write crashed with:
    #   "prepared statement '_pg3_X' does not exist"
    #
    # The correct psycopg3 fix is prepare_threshold=0, which tells the driver
    # never to promote queries to prepared statements. This CANNOT be set via
    # a URI query parameter — psycopg3 raises ProgrammingError for unknown
    # URI params (which is why "?prepared_statements=false" failed).
    #
    # Instead we open the psycopg3 connection manually with the keyword arg
    # and pass the live connection object directly to PostgresSaver().
    #   prepare_threshold=0  -> never prepare (safe, tiny parse overhead per query)
    #   autocommit=True      -> required by PostgresSaver (it manages transactions)
    from psycopg import Connection as Psycopg3Connection

    # Open connection manually so we can pass prepare_threshold=0 directly.
    # from_conn_string() does not expose connection kwargs in this version of
    # langgraph-checkpoint-postgres, and prepare_threshold cannot be set via URI.
    _pg_conn = Psycopg3Connection.connect(
        POSTGRES_URI,
        autocommit=True,
        prepare_threshold=0,
    )

    # Reset any stale prepared statements left by a pooler-recycled session.
    # We use prepared=False so this single statement never itself gets prepared.
    _pg_conn.execute("DEALLOCATE ALL", prepare=False)

    memory = PostgresSaver(_pg_conn)

    try:
        # ── One-time idempotent table bootstrap ────────────────────────────
        memory.setup()
        print("\n  ✅  Checkpoint store ready (Supabase Postgres).")

        # ── Build graph with checkpointer injected ─────────────────────────
        graph = build_graph(memory)

        # ── Terminal UI ────────────────────────────────────────────────────
        print("\n" + "=" * 62)
        print("  🌿  The Body Shop — Virtual Skincare Consultant")
        print("       Plan-and-Execute · Self-Healing Re-Planner · Groq")
        print("=" * 62)

        try:
            phone_number = input(
                "\n  Please enter your phone number to start the session: "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  👋  Goodbye! Stay glowing.\n")
            raise SystemExit(0)

        if not phone_number:
            phone_number = "guest-session"

        # thread_id scopes all checkpoints to this customer.
        # Returning customers automatically resume their last session.
        config = {"configurable": {"thread_id": phone_number}}

        print(f"\n  🔐  Session started for: {phone_number}")
        print("  Type your question below. Type 'exit' to quit.\n")

        # FIX 2: conversation_history is only used as a local in-process
        # buffer for the AIMessage appends. The real durable history lives
        # inside the LangGraph checkpoint (keyed by thread_id = phone_number).
        # On process restart the checkpointer restores full state automatically.
        conversation_history: List = []

        while True:
            print(DIVIDER)

            try:
                user_input = input("  You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\n  👋  Goodbye! Stay glowing.\n")
                break

            if user_input.lower() in {"exit", "quit", "q"}:
                print("\n  👋  Thank you for visiting The Body Shop. Goodbye!\n")
                break

            if not user_input:
                print("  ⚠️   Please enter a message.")
                continue

            conversation_history.append(HumanMessage(content=user_input))

            # FIX 2: phone_number is now a first-class field in AgentState.
            # Every graph invocation carries it so the planner node can inject
            # it into the session context prompt — preventing hallucinated numbers.
            initial_state: AgentState = {
                "messages"    : conversation_history,
                "plan"        : [],
                "past_steps"  : [],
                "response"    : "",
                "phone_number": phone_number,
            }

            print("\n  ⏳  Building plan...\n")

            try:
                final_state = graph.invoke(initial_state, config=config)
            except Exception as e:
                print(f"\n  ❌  Graph execution error: {e}\n")
                continue

            final_response = final_state.get("response", "")

            if final_response:
                print(BOT_PREFIX)
                for line in final_response.splitlines():
                    print(f"    {line}")
                print()
                conversation_history.append(AIMessage(content=final_response))
            else:
                print("\n  ⚠️   No final response generated. Check re-planner logs above.\n")

            # ── Debug: execution summary printed after every turn ──────────
            past_steps = final_state.get("past_steps", [])
            if past_steps:
                print(f"  📊  Execution summary — {len(past_steps)} step(s) completed:")
                for i, (task, obs) in enumerate(past_steps, 1):
                    obs_preview = obs[:90] + "..." if len(obs) > 90 else obs
                    print(f"       {i}. {task[:60]}{'...' if len(task) > 60 else ''}")
                    print(f"          -> {obs_preview}")
                print()    
    finally:
        _pg_conn.close()