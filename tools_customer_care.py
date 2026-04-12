# tools_customer_care.py
# LangChain Tool — Order Status Lookup for Customer Care Agent
# Queries the Supabase orders table via psycopg2 and returns a
# formatted status string the agent can relay directly to the customer.

import os
import psycopg2
from dotenv import load_dotenv
from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Load environment variables (.env must define POSTGRES_URI)
# ---------------------------------------------------------------------------
load_dotenv()


# ===========================================================================
# TOOL: Order Status Lookup
# ===========================================================================

@tool
def get_order_status(order_id: str) -> str:
    """
    Retrieves the current shipping and delivery status of a customer's
    Body Shop order from the database. Use this tool whenever a customer
    asks about any of the following:
        - Where is my order?
        - What is the status of my order / delivery?
        - Has my order shipped yet?
        - Can you give me a tracking link / number?
        - When will my order arrive / be delivered?
        - My order hasn't arrived yet — what's happening?

    INSTRUCTIONS FOR THE AGENT:
    - You MUST extract the order_id from the user's message before calling
      this tool. Body Shop order IDs follow the format 'TBS-XXXX'
      (e.g., 'TBS-9901', 'TBS-9915'). Scan the user's message for this
      pattern and pass it exactly — do not alter the casing or format.
    - If the user mentions an order but does NOT provide an order ID,
      do NOT call this tool yet. Instead, ask the user:
      "Could you please share your order number? It should be in the
       format TBS-XXXX and can be found in your confirmation email."
    - If the tool returns a 'No order found' message, apologise and ask
      the user to double-check their order number before escalating.
    - Status meanings you should communicate to the customer:
        • Processing       — Order confirmed, being packed at the warehouse.
        • Shipped          — Handed to the courier, on its way.
        • Out for Delivery — With the delivery agent today; expect delivery
                             by end of day.
        • Delivered        — Successfully delivered to the address on file.
        • Cancelled        — Order was cancelled; advise customer to contact
                             support for a refund update.
        • Return Initiated — A return has been logged and is being processed.

    Args:
        order_id (str): The Body Shop order ID in the format 'TBS-XXXX',
                        extracted directly from the customer's message.

    Returns:
        str: A formatted order status string ready to be read to the
             customer, or a not-found message with guidance for the agent.
    """
    conn   = None
    cursor = None

    try:
        # -------------------------------------------------------------------
        # Establish database connection
        # -------------------------------------------------------------------
        conn   = psycopg2.connect(os.getenv("POSTGRES_URI"))
        cursor = conn.cursor()

        # -------------------------------------------------------------------
        # Parameterised query — safe against SQL injection
        # Joining customers to surface the customer name for richer responses
        # -------------------------------------------------------------------
        cursor.execute(
            """
            SELECT
                o.order_id,
                o.status,
                o.estimated_delivery,
                o.tracking_link,
                c.name          AS customer_name
            FROM  public.orders    o
            JOIN  public.customers c USING (phone_number)
            WHERE o.order_id = %s;
            """,
            (order_id.strip().upper(),)   # normalise input casing defensively
        )

        row = cursor.fetchone()

        # -------------------------------------------------------------------
        # Order not found
        # -------------------------------------------------------------------
        if not row:
            return (
                f"No order found with ID '{order_id}'. "
                "Please ask the user to verify their order number — it should "
                "be in the format TBS-XXXX and is available in their "
                "confirmation email or the Body Shop app."
            )

        # -------------------------------------------------------------------
        # Unpack result row
        # -------------------------------------------------------------------
        db_order_id, status, estimated_delivery, tracking_link, customer_name = row

        # Format estimated delivery date as a readable string (e.g. 28 Jun 2025)
        delivery_str = (
            estimated_delivery.strftime("%d %b %Y")
            if estimated_delivery else "Not available"
        )

        # Handle NULL tracking links gracefully
        tracking_str = (
            f"Track your order here → {tracking_link}"
            if tracking_link
            else "Tracking is not yet available — "
                 "it will be updated once your order is shipped."
        )

        # -------------------------------------------------------------------
        # Compose the formatted response string
        # -------------------------------------------------------------------
        return (
            f"Order Status Update for {customer_name}\n"
            f"{'─' * 44}\n"
            f"  Order ID           : {db_order_id}\n"
            f"  Current Status     : {status}\n"
            f"  Estimated Delivery : {delivery_str}\n"
            f"  Tracking           : {tracking_str}"
        )

    # -----------------------------------------------------------------------
    # Granular exception handling — surfaces useful errors to the agent
    # -----------------------------------------------------------------------
    except psycopg2.OperationalError as e:
        return (
            f"Database connection error while looking up order '{order_id}': {e}. "
            "Please check the POSTGRES_URI in your .env file."
        )
    except psycopg2.Error as e:
        return f"Database query error for order '{order_id}': {e}"
    except Exception as e:
        return f"Unexpected error while retrieving order '{order_id}': {e}"

    # -----------------------------------------------------------------------
    # Always release DB resources — even if an exception was raised
    # -----------------------------------------------------------------------
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

'''
# ===========================================================================
# LOCAL TEST HARNESS
# Run:  python tools_customer_care.py
# ===========================================================================
if __name__ == "__main__":
    DIVIDER = "=" * 55

    print(DIVIDER)
    print("TOOL TEST — tools_customer_care.py")
    print(DIVIDER)

    # ------------------------------------------------------------------
    # Test 1 — Out for Delivery order (Aarav Sharma, has tracking link)
    # Expected: Status + BlueDart tracking URL
    # ------------------------------------------------------------------
    print("\n[TEST 1] Out for Delivery order — TBS-9901\n")
    print(get_order_status.invoke({"order_id": "TBS-9901"}))

    print(f"\n{'-' * 55}")

    # ------------------------------------------------------------------
    # Test 2 — Processing order (no tracking link yet)
    # Expected: Status with graceful 'tracking not yet available' message
    # ------------------------------------------------------------------
    print("\n[TEST 2] Processing order (no tracking) — TBS-9904\n")
    print(get_order_status.invoke({"order_id": "TBS-9904"}))

    print(f"\n{'-' * 55}")

    # ------------------------------------------------------------------
    # Test 3 — Cancelled order
    # Expected: Cancelled status, agent should advise customer on refund
    # ------------------------------------------------------------------
    print("\n[TEST 3] Cancelled order — TBS-9911\n")
    print(get_order_status.invoke({"order_id": "TBS-9911"}))

    print(f"\n{'-' * 55}")

    # ------------------------------------------------------------------
    # Test 4 — Return Initiated order (Vikram Nair)
    # Expected: Return status with Delhivery tracking link
    # ------------------------------------------------------------------
    print("\n[TEST 4] Return Initiated order — TBS-9907\n")
    print(get_order_status.invoke({"order_id": "TBS-9907"}))

    print(f"\n{'-' * 55}")

    # ------------------------------------------------------------------
    # Test 5 — Lowercase input (normalisation guard test)
    # Expected: Same result as Test 1 — strip+upper handles 'tbs-9901'
    # ------------------------------------------------------------------
    print("\n[TEST 5] Lowercase order ID input — 'tbs-9901'\n")
    print(get_order_status.invoke({"order_id": "tbs-9901"}))

    print(f"\n{'-' * 55}")

    # ------------------------------------------------------------------
    # Test 6 — Non-existent order ID (not-found path)
    # Expected: Polite not-found message with format guidance
    # ------------------------------------------------------------------
    print("\n[TEST 6] Non-existent order ID — TBS-0000\n")
    print(get_order_status.invoke({"order_id": "TBS-0000"}))

    print(f"\n{DIVIDER}")
'''