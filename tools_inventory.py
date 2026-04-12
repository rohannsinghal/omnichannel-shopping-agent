# tools_inventory.py
"""
LangGraph Agent Tool: Real-Time SQL Inventory Check via Supabase PostgreSQL.

This module defines the `check_sql_inventory` tool, which is used by the
LangGraph agent to query live stock levels from a Supabase-hosted PostgreSQL
database. It is designed to be chained after `search_chroma_products` in a
multi-step agentic workflow.
"""

import os
import psycopg2
from langchain_core.tools import tool


@tool
def check_sql_inventory(product_id: str) -> str:
    """
    Checks the real-time stock and inventory level of a specific product
    in the retail database using its unique product ID.

    IMPORTANT — How to use this tool correctly:
    You MUST call `search_chroma_products` first to retrieve valid product
    results. Then, extract the exact `product_id` value (e.g., "TBS_029")
    from those results and pass it directly into this tool. Do NOT guess,
    infer, or fabricate a product_id — only use IDs returned by the catalog
    search tool.

    When to trigger this tool:
    - The user explicitly asks whether a product is in stock or available.
    - The user asks "Can I buy this?", "Is this available?", or "Do you
      have this?" after a product has been identified.
    - The user wants to know the quantity or stock level of a product.
    - You have already identified a product via `search_chroma_products`
      and need to confirm its current availability before recommending it.
    - The user is ready to make a purchase decision and availability is a
      deciding factor.

    Do NOT use this tool for:
    - Browsing or discovering products — use `search_chroma_products` first.
    - Checking stock without a confirmed product_id from the catalog tool.
    - General questions about skincare, ingredients, or product types.

    Correct usage pattern (chain these tools in order):
      Step 1 → `search_chroma_products("moisturiser for dry skin")`
      Step 2 → Extract `product_id` from results, e.g., "TBS_029"
      Step 3 → `check_sql_inventory("TBS_029")`

    Args:
        product_id (str): The exact, unique product identifier string obtained
                          from a prior call to `search_chroma_products`. This
                          value is case-sensitive and must match the format
                          stored in the database (e.g., "TBS_029", "TBS_104").

    Returns:
        str: A plain-text sentence reporting the product's name and current
             stock quantity. Returns a not-found message if the product_id
             does not exist in the inventory table, or a descriptive error
             message if the database connection fails.
             Examples:
               - "Vitamin C Glow Serum (ID: TBS_029) currently has 42 units in stock."
               - "Product ID not found in inventory."
               - "Error: Could not connect to the inventory database. ..."
    """

    # Initialise connection and cursor to None so the finally block can
    # safely check their state regardless of where an exception is raised.
    connection = None
    cursor = None

    try:
        # --- 1. Establish Database Connection ---
        # Load the full Supabase PostgreSQL connection URI from the environment
        # and open a connection using psycopg2. The URI format is:
        # postgresql://user:password@host:port/database
        connection = psycopg2.connect(
            os.getenv("POSTGRES_URI"),
            options="-c prepare_threshold=0" 
        )

        # Open a standard cursor for executing SQL statements.
        cursor = connection.cursor()
        cursor.execute("DEALLOCATE ALL")

        # --- 2. Execute Parameterised SQL Query ---
        # Using %s placeholders with a parameter tuple is the correct
        # psycopg2 pattern for parameterised queries. This prevents SQL
        # injection by ensuring the product_id is always treated as a
        # data value and never interpreted as executable SQL.
        query = "SELECT name, stock_quantity FROM inventory WHERE product_id = %s"
        cursor.execute(query, (product_id,))  # Note the tuple: (product_id,)

        # Fetch a single matching row. Returns None if no row is found.
        row = cursor.fetchone()

        # --- 3. Format and Return Result ---
        if row:
            # Unpack the two selected columns from the returned row tuple.
            name, stock_quantity = row
            return (
                f"{name} (ID: {product_id}) currently has "
                f"{stock_quantity} units in stock."
            )
        else:
            # The product_id was not found in the inventory table.
            # This could mean the catalog and inventory are out of sync,
            # or an incorrect product_id was passed in.
            return "Product ID not found in inventory."

    except psycopg2.OperationalError as e:
        # Catch connection-level failures specifically (wrong URI, network
        # issues, Supabase authentication failure, etc.) and return a
        # descriptive message so the agent can inform the user gracefully.
        return (
            f"Error: Could not connect to the inventory database. "
            f"Please verify your POSTGRES_URI environment variable. "
            f"Technical details: {str(e)}"
        )

    except Exception as e:
        # Catch-all for any unexpected errors during query execution or
        # result processing, ensuring the agent never crashes mid-workflow.
        return (
            f"Error: An unexpected error occurred while checking inventory "
            f"for product ID '{product_id}'. Technical details: {str(e)}"
        )

    finally:
        # --- 4. Guaranteed Resource Cleanup ---
        # The finally block ALWAYS executes, even if an exception was raised.
        # This ensures the cursor and connection are closed properly every
        # time, preventing connection leaks and database locking issues that
        # could degrade Supabase performance over time.
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

'''
# ---------------------------------------------------------------------------
# Local Test Block
# ---------------------------------------------------------------------------
# This block only runs when the file is executed directly (e.g., via
# `python tools_inventory.py`). It is ignored when the module is imported
# by the main agent script. Use this to validate your database connection
# and query logic independently before wiring the tool into the agent.
#
# Pre-requisite: Ensure your .env file is populated and loaded.
# Run from terminal: python tools_inventory.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from dotenv import load_dotenv

    # Load environment variables from the local .env file for the test run.
    load_dotenv()

    print("=" * 55)
    print("  tools_inventory.py — Local Connectivity Test")
    print("=" * 55)

    # --- Test Case 1: Known valid product ID ---
    test_id_valid = "TBS_029"
    print(f"\n[TEST 1] Querying inventory for product_id: '{test_id_valid}'")
    result_valid = check_sql_inventory.invoke({"product_id": test_id_valid})
    print(f"[RESULT] {result_valid}")

    # --- Test Case 2: Non-existent product ID ---
    test_id_invalid = "TBS_999"
    print(f"\n[TEST 2] Querying inventory for product_id: '{test_id_invalid}'")
    result_invalid = check_sql_inventory.invoke({"product_id": test_id_invalid})
    print(f"[RESULT] {result_invalid}")

    print("\n" + "=" * 55)
    print("  Test complete.")
    print("=" * 55)
'''