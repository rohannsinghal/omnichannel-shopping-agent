# tools_commerce.py
# LangChain Tools for Commerce & Loyalty — Supabase / PostgreSQL
# Covers: loyalty profile lookup, cart management, and checkout generation.

import os
import uuid
import psycopg2
from dotenv import load_dotenv
from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Load environment variables (.env must define POSTGRES_URI)
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Shared DB helper — keeps connection logic in one place
# ---------------------------------------------------------------------------

def _get_connection():
    """Opens and returns a psycopg2 connection from POSTGRES_URI."""
    return psycopg2.connect(os.getenv("POSTGRES_URI"))

# ===========================================================================
# TOOL 1 — Loyalty Profile Lookup
# ===========================================================================

@tool
def get_loyalty_profile(phone_number: str) -> str:
    """
    Retrieves a customer's Body Shop loyalty profile from the database,
    including their name, current membership tier, and accumulated loyalty points.

    INSTRUCTIONS FOR THE AGENT:
    - You MUST ask the user for their registered phone number before calling
      this tool. Do NOT guess or fabricate a phone number.
    - Phone numbers are stored in E.164 format (e.g. '+919810001001'). If the
      user provides a 10-digit Indian mobile number, prepend '+91' before
      passing it to this tool.
    - Membership tiers and their benefits:
        • Standard  — 0 – 499 pts  — Base earn rate
        • Silver    — 500 – 1499 pts — 1.25× bonus points on purchases
        • Gold      — 1500+ pts      — 1.5× bonus points + free gift wrapping
    - Use the returned loyalty_points value when the user asks how much
      discount they can redeem (conversion rate: 10 points = ₹1).

    Args:
        phone_number (str): Customer's E.164 phone number, e.g. '+919810001001'.

    Returns:
        str: Formatted loyalty profile, or a clear error / not-found message.
    """
    conn = cursor = None
    try:
        conn   = _get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT name, membership_tier, loyalty_points
            FROM   public.customers
            WHERE  phone_number = %s;
            """,
            (phone_number,)
        )
        row = cursor.fetchone()

        if not row:
            return (
                f"No account found for phone number {phone_number}. "
                "Please double-check the number or ask the customer to register."
            )

        name, tier, points = row
        redeemable_inr     = points // 10  # 10 pts = ₹1

        return (
            f"👤 Loyalty Profile Found\n"
            f"   Name            : {name}\n"
            f"   Membership Tier : {tier}\n"
            f"   Loyalty Points  : {points:,} pts\n"
            f"   Redeemable Value: ₹{redeemable_inr:,} "
            f"({points:,} pts ÷ 10)"
        )

    except psycopg2.OperationalError as e:
        return f"Database connection error: {e}"
    except psycopg2.Error as e:
        return f"Database query error: {e}"
    except Exception as e:
        return f"Unexpected error in get_loyalty_profile: {e}"
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ===========================================================================
# TOOL 2 — Add Item to Cloud Cart
# ===========================================================================

@tool
def add_to_cart(phone_number: str, product_id: str) -> str:
    """
    Adds a specific product to the customer's persistent cloud shopping cart
    stored in Supabase, enabling true omnichannel continuity (the cart is
    shared across web, app, and in-store channels).

    INSTRUCTIONS FOR THE AGENT:
    - Only call this tool after you have BOTH the customer's phone number AND
      a valid product_id returned by search_chroma_products / check_sql_inventory.
    - Never invent or guess a product_id. Only use IDs from prior tool results.
    - Product IDs follow the format TBS_XXX (e.g. TBS_029, TBS_049).
    - If a product is already in the cart, the quantity will be incremented
      by 1 automatically (upsert behaviour). Inform the user accordingly.
    - Always confirm the product name and price back to the user after a
      successful add, so they know exactly what was added.

    Args:
        phone_number (str): Customer's E.164 phone number.
        product_id   (str): Exact product ID from search_chroma_products results.

    Returns:
        str: Success confirmation with product details, or an error message.
    """
    conn = cursor = None

    try:
        conn   = _get_connection()
        cursor = conn.cursor()

        # FIX 4: Resolve product name and price from the live inventory table
        # instead of the hardcoded PRODUCT_CATALOGUE dict. The catalogue used
        # TBS-XXX-NNN format IDs which never matched ChromaDB's TBS_NNN format,
        # causing every add_to_cart call from the agent to fail silently with
        # "Unknown product_id". The inventory table uses TBS_NNN — the same IDs
        # returned by search_chroma_products and check_sql_inventory.
        cursor.execute(
            "SELECT name, price FROM public.inventory WHERE product_id = %s;",
            (product_id,)
        )
        product_row = cursor.fetchone()
        if not product_row:
            return (
                f"Unknown product_id '{product_id}'. "
                "Please use a product_id returned by the search_chroma_products tool."
            )
        product_name, product_price = product_row

        # Verify the customer account exists before writing to cart
        cursor.execute(
            "SELECT name FROM public.customers WHERE phone_number = %s;",
            (phone_number,)
        )
        customer = cursor.fetchone()
        if not customer:
            return (
                f"No customer account found for {phone_number}. "
                "The item was not added to the cart."
            )

        customer_name = customer[0]

        # Upsert — if the row exists, increment quantity; otherwise insert.
        # The unique index idx_cart_unique_item(phone_number, product_id)
        # makes the conflict target precise and safe.
        cursor.execute(
            """
            INSERT INTO public.shopping_cart
                        (cart_id, phone_number, product_id, quantity, added_at)
            VALUES      (%s, %s, %s, 1, NOW())
            ON CONFLICT (phone_number, product_id)
            DO UPDATE SET quantity = shopping_cart.quantity + 1;
            """,
            (str(uuid.uuid4()), phone_number, product_id)
        )
        conn.commit()

        # Re-fetch the updated quantity for an accurate confirmation message
        cursor.execute(
            """
            SELECT quantity FROM public.shopping_cart
            WHERE  phone_number = %s AND product_id = %s;
            """,
            (phone_number, product_id)
        )
        qty = cursor.fetchone()[0]

        return (
            f"✅ Cart Updated for {customer_name}\n"
            f"   Product  : {product_name}\n"
            f"   Price    : ₹{product_price:,} per unit\n"
            f"   Quantity : {qty} in cart\n"
            f"   Subtotal : ₹{product_price * qty:,}"
        )

    except psycopg2.OperationalError as e:
        return f"Database connection error: {e}"
    except psycopg2.Error as e:
        if conn: conn.rollback()
        return f"Database error while adding to cart: {e}"
    except Exception as e:
        return f"Unexpected error in add_to_cart: {e}"
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ===========================================================================
# TOOL 2b — View Cart Contents
# ===========================================================================

@tool
def view_cart(phone_number: str) -> str:
    """
    Returns the full contents of a customer's shopping cart, including product
    names, quantities, unit prices, line totals, and the timestamp when each
    item was added.

    INSTRUCTIONS FOR THE AGENT:
    - Call this tool whenever the user asks to see, view, or check their cart.
    - Use the returned `added_at` timestamps to explain when items were added
      if the user asks (e.g. "You added this 2 hours ago").
    - If the cart is empty, inform the user politely and suggest browsing
      the catalogue with search_chroma_products.
    - Do NOT call add_to_cart after view_cart unless the user gives an
      explicit add instruction.

    Args:
        phone_number (str): Customer's E.164 phone number, e.g. '+919810001001'.

    Returns:
        str: Formatted cart summary with all items, quantities, prices, and
             timestamps, or a message indicating the cart is empty.
    """
    conn = cursor = None
    try:
        conn   = _get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                sc.product_id,
                inv.name,
                sc.quantity,
                inv.price,
                sc.added_at
            FROM   public.shopping_cart sc
            JOIN   public.inventory     inv ON inv.product_id = sc.product_id
            WHERE  sc.phone_number = %s
            ORDER  BY sc.added_at;
            """,
            (phone_number,)
        )
        rows = cursor.fetchall()

        if not rows:
            return (
                f"🛒 The cart for {phone_number} is currently empty. "
                "Add products to get started!"
            )

        lines   = [f"🛒 Cart for {phone_number}:\n"]
        total   = 0
        for i, (product_id, name, qty, price, added_at) in enumerate(rows, 1):
            line_total = price * qty
            total     += line_total
            ts = added_at.strftime("%d %b %Y %H:%M") if added_at else "unknown"
            lines.append(
                f"  {i}. {name} (ID: {product_id})\n"
                f"     Qty: {qty} × ₹{price:,} = ₹{line_total:,}\n"
                f"     Added: {ts}"
            )

        lines.append(f"\n  {'─'*38}")
        lines.append(f"  Cart Total: ₹{total:,}  ({len(rows)} item(s))")
        return "\n".join(lines)

    except psycopg2.OperationalError as e:
        return f"Database connection error: {e}"
    except psycopg2.Error as e:
        return f"Database query error in view_cart: {e}"
    except Exception as e:
        return f"Unexpected error in view_cart: {e}"
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ===========================================================================
# TOOL 2c — Remove Item from Cart
# ===========================================================================

@tool
def remove_from_cart(phone_number: str, product_id: str) -> str:
    """
    Removes a specific product from the customer's shopping cart.

    INSTRUCTIONS FOR THE AGENT:
    - Call this tool ONLY when the user explicitly asks to remove or delete
      a specific item from their cart (e.g. "remove the serum", "delete TBS_029").
    - Always confirm the removal to the user after this tool succeeds.
    - If the item was not in the cart, surface the message to the user politely.
    - Never remove items speculatively — always get explicit confirmation first.

    Args:
        phone_number (str): Customer's E.164 phone number.
        product_id   (str): Exact product ID to remove (e.g. 'TBS_029').

    Returns:
        str: Confirmation that the item was removed, or a message if it was
             not found in the cart.
    """
    conn = cursor = None
    try:
        conn   = _get_connection()
        cursor = conn.cursor()

        # Resolve product name for a friendlier confirmation message
        cursor.execute(
            "SELECT name FROM public.inventory WHERE product_id = %s;",
            (product_id,)
        )
        inv_row = cursor.fetchone()
        product_name = inv_row[0] if inv_row else product_id

        cursor.execute(
            """
            DELETE FROM public.shopping_cart
            WHERE  phone_number = %s AND product_id = %s;
            """,
            (phone_number, product_id)
        )
        deleted = cursor.rowcount
        conn.commit()

        if deleted == 0:
            return (
                f"'{product_name}' was not found in the cart for {phone_number}. "
                "No changes were made."
            )

        return (
            f"✅ Removed from cart: {product_name} (ID: {product_id})\n"
            f"   Cart updated for {phone_number}."
        )

    except psycopg2.OperationalError as e:
        return f"Database connection error: {e}"
    except psycopg2.Error as e:
        if conn: conn.rollback()
        return f"Database error in remove_from_cart: {e}"
    except Exception as e:
        return f"Unexpected error in remove_from_cart: {e}"
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ===========================================================================
# TOOL 3 — Checkout & Order Summary
# ===========================================================================

@tool
def checkout_cart(phone_number: str) -> str:
    """
    Generates a complete order summary for the customer's current cart,
    applies any loyalty point redemption discount, calculates the final
    payable amount, and returns a mock Stripe checkout link to complete
    the payment.

    INSTRUCTIONS FOR THE AGENT:
    - Call this tool ONLY when the user explicitly says they want to
      checkout, pay, or complete their purchase.
    - Before calling, confirm with the user whether they want to redeem
      their loyalty points. This tool automatically applies the maximum
      redeemable discount from their available points.
    - After returning the checkout link, tell the user the link is valid
      for 30 minutes and that their cart will be cleared once payment
      is confirmed.
    - Loyalty conversion rate: 10 points = ₹1 discount (applied to total).
    - If the cart is empty, prompt the user to add items before checking out.

    Args:
        phone_number (str): Customer's E.164 phone number.

    Returns:
        str: Full order summary with itemised breakdown, loyalty discount,
             final total, and a mock Stripe payment link.
    """
    conn = cursor = None
    try:
        conn   = _get_connection()
        cursor = conn.cursor()

        # ── Step 1: Fetch cart items ────────────────────────────────────────
        cursor.execute(
            """
            SELECT product_id, quantity
            FROM   public.shopping_cart
            WHERE  phone_number = %s
            ORDER  BY added_at;
            """,
            (phone_number,)
        )
        cart_rows = cursor.fetchall()

        if not cart_rows:
            return (
                f"🛒 The cart for {phone_number} is empty. "
                "Please add products before checking out."
            )

        # ── Step 2: Fetch customer loyalty profile ──────────────────────────
        cursor.execute(
            """
            SELECT name, membership_tier, loyalty_points
            FROM   public.customers
            WHERE  phone_number = %s;
            """,
            (phone_number,)
        )
        customer_row = cursor.fetchone()

        if not customer_row:
            return (
                f"No customer account found for {phone_number}. "
                "Cannot proceed with checkout."
            )

        customer_name, tier, loyalty_points = customer_row

        # ── Step 3: Build itemised order summary ────────────────────────────
        # FIX 4: Resolve product name and price from the live inventory table
        # instead of the stale hardcoded PRODUCT_CATALOGUE dict, so cart items
        # added via search_chroma_products (TBS_XXX IDs) are resolved correctly.
        order_lines   = []
        subtotal      = 0
        unknown_items = []

        for product_id, qty in cart_rows:
            cursor.execute(
                "SELECT name, price FROM public.inventory WHERE product_id = %s;",
                (product_id,)
            )
            inv_row = cursor.fetchone()
            if not inv_row:
                unknown_items.append(product_id)
                continue
            product_name, unit_price = inv_row
            line_total = unit_price * qty
            subtotal  += line_total
            order_lines.append(
                f"   • {product_name}\n"
                f"     {qty} × ₹{unit_price:,} = ₹{line_total:,}"
            )

        if not order_lines:
            return (
                "Cart contains unrecognised product IDs: "
                f"{', '.join(unknown_items)}. Please review the cart."
            )

        # ── Step 4: Loyalty discount calculation ────────────────────────────
        # Maximum redeemable = all available points converted to INR
        max_discount        = loyalty_points // 10     # 10 pts = ₹1
        loyalty_discount    = min(max_discount, subtotal)  # can't exceed order total
        points_redeemed     = loyalty_discount * 10
        final_total         = subtotal - loyalty_discount

        # ── Step 5: Mock Stripe payment link ────────────────────────────────
        # In production: call stripe.checkout.Session.create(...)
        mock_session_id  = uuid.uuid4().hex[:16]
        stripe_link      = f"https://checkout.stripe.com/pay/test_{mock_session_id}"

        # ── Step 6: Compose the output string ───────────────────────────────
        item_block       = "\n".join(order_lines)
        unknown_warning  = (
            f"\n   ⚠️  Skipped unrecognised items: {', '.join(unknown_items)}"
            if unknown_items else ""
        )

        return (
            f"🧾 Order Summary for {customer_name} ({tier} Member)\n"
            f"{'─' * 48}\n"
            f"{item_block}"
            f"{unknown_warning}\n"
            f"{'─' * 48}\n"
            f"   Subtotal         : ₹{subtotal:,}\n"
            f"   Loyalty Discount : ₹{loyalty_discount:,} "
            f"({points_redeemed:,} pts redeemed)\n"
            f"   Points Remaining : {loyalty_points - points_redeemed:,} pts\n"
            f"{'─' * 48}\n"
            f"   💳 TOTAL PAYABLE : ₹{final_total:,}\n"
            f"{'─' * 48}\n"
            f"   🔗 Complete Payment:\n"
            f"   {stripe_link}\n"
            f"\n   ⏳ Link expires in 30 minutes. "
            f"Cart will clear on payment confirmation."
        )

    except psycopg2.OperationalError as e:
        return f"Database connection error: {e}"
    except psycopg2.Error as e:
        return f"Database query error during checkout: {e}"
    except Exception as e:
        return f"Unexpected error in checkout_cart: {e}"
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ===========================================================================
# TOOL 4 — Create New Customer Account
# ===========================================================================

@tool
def create_user_account(phone_number: str, name: str) -> str:
    """
    Creates a new customer account in the Body Shop loyalty database.
    New accounts start at the Standard membership tier with 0 loyalty points.

    INSTRUCTIONS FOR THE AGENT:
    - Call this tool ONLY when the user explicitly asks to register or create
      a new account, OR when get_loyalty_profile / add_to_cart returns a
      "No account found" error and the user confirms they want to register.
    - You MUST collect BOTH the customer's phone number AND their name before
      calling this tool. Do NOT invent or guess either value.
    - Phone numbers must be in E.164 format (e.g. '+919810001001'). If the
      user provides a 10-digit Indian mobile number, prepend '+91'.
    - If an account already exists for the given phone number, inform the
      user and do NOT create a duplicate.
    - After successful creation, confirm the name, phone number, and starting
      tier (Standard, 0 points) back to the user.

    Args:
        phone_number (str): Customer's E.164 phone number, e.g. '+919810001001'.
        name         (str): Customer's full name as they provided it.

    Returns:
        str: Success confirmation with account details, or an error message.
    """
    conn = cursor = None
    try:
        conn   = _get_connection()
        cursor = conn.cursor()

        # Check if account already exists to prevent duplicates
        cursor.execute(
            "SELECT name FROM public.customers WHERE phone_number = %s;",
            (phone_number,)
        )
        existing = cursor.fetchone()
        if existing:
            return (
                f"An account already exists for {phone_number} "
                f"(registered as '{existing[0]}'). "
                "No new account was created."
            )

        # Insert new customer — Standard tier, 0 points
        cursor.execute(
            """
            INSERT INTO public.customers (phone_number, name, membership_tier, loyalty_points)
            VALUES (%s, %s, 'Standard', 0);
            """,
            (phone_number, name)
        )
        conn.commit()

        return (
            f"✅ Account Created Successfully\n"
            f"   Name            : {name}\n"
            f"   Phone Number    : {phone_number}\n"
            f"   Membership Tier : Standard\n"
            f"   Loyalty Points  : 0 pts\n"
            f"\n   Welcome to The Body Shop Loyalty Programme! "
            f"Earn points on every purchase to unlock Silver and Gold tier benefits."
        )

    except psycopg2.OperationalError as e:
        return f"Database connection error: {e}"
    except psycopg2.IntegrityError as e:
        if conn: conn.rollback()
        return (
            f"Account creation failed — a record for {phone_number} may already exist. "
            f"Details: {e}"
        )
    except psycopg2.Error as e:
        if conn: conn.rollback()
        return f"Database error while creating account: {e}"
    except Exception as e:
        return f"Unexpected error in create_user_account: {e}"
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


'''
# ===========================================================================
# LOCAL TEST HARNESS
# Run:  python tools_commerce.py
# Uses Aarav Sharma — Gold tier, 3200 pts (+919810001001)
# ===========================================================================
if __name__ == "__main__":
    TEST_PHONE = "+919810001001"   # Aarav Sharma — Gold, 3200 pts
    DIVIDER    = "=" * 55

    print(DIVIDER)
    print("TOOL TEST — tools_commerce.py")
    print(DIVIDER)

    # ------------------------------------------------------------------
    # Test 1 — Loyalty profile lookup
    # Expected: Gold tier, 3200 pts, ₹320 redeemable
    # ------------------------------------------------------------------
    print("\n[TEST 1] get_loyalty_profile\n")
    print(get_loyalty_profile.invoke({"phone_number": TEST_PHONE}))

    print(f"\n{'-' * 55}")

    # ------------------------------------------------------------------
    # Test 2a — Add first product to cart
    # Expected: 1× Fuji Green Tea Cleanser, subtotal ₹850
    # ------------------------------------------------------------------
    print("\n[TEST 2a] add_to_cart — first item\n")
    print(add_to_cart.invoke({
        "phone_number": TEST_PHONE,
        "product_id":   "TBS-TEA-001"
    }))

    print(f"\n{'-' * 55}")

    # ------------------------------------------------------------------
    # Test 2b — Add second product to cart
    # Expected: 1× Vitamin C Glow Serum, subtotal ₹1,450
    # ------------------------------------------------------------------
    print("\n[TEST 2b] add_to_cart — second item\n")
    print(add_to_cart.invoke({
        "phone_number": TEST_PHONE,
        "product_id":   "TBS-VIT-003"
    }))

    print(f"\n{'-' * 55}")

    # ------------------------------------------------------------------
    # Test 2c — Add duplicate item (upsert test)
    # Expected: quantity increments to 2, subtotal ₹1,700
    # ------------------------------------------------------------------
    print("\n[TEST 2c] add_to_cart — duplicate item (upsert)\n")
    print(add_to_cart.invoke({
        "phone_number": TEST_PHONE,
        "product_id":   "TBS-TEA-001"
    }))

    print(f"\n{'-' * 55}")

    # ------------------------------------------------------------------
    # Test 2d — Invalid product ID (guard test)
    # Expected: clear error listing valid IDs
    # ------------------------------------------------------------------
    print("\n[TEST 2d] add_to_cart — invalid product_id\n")
    print(add_to_cart.invoke({
        "phone_number": TEST_PHONE,
        "product_id":   "TBS-INVALID-999"
    }))

    print(f"\n{'-' * 55}")

    # ------------------------------------------------------------------
    # Test 3 — Checkout
    # Cart: 2× TBS-TEA-001 (₹1,700) + 1× TBS-VIT-003 (₹1,450) = ₹3,150
    # Gold loyalty: 3200 pts → ₹320 discount → final ₹2,830
    # ------------------------------------------------------------------
    print("\n[TEST 3] checkout_cart\n")
    print(checkout_cart.invoke({"phone_number": TEST_PHONE}))

    print(f"\n{DIVIDER}")
'''