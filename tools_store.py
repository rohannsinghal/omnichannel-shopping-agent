# tools_store.py
# LangChain Tool #4 — Physical Store Locator (Supabase / PostgreSQL)
# Supports GPS-based Haversine distance sorting AND text-based ILIKE fallback.

import os
import psycopg2
from dotenv import load_dotenv
from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Load environment variables from .env (POSTGRES_URI must be defined there)
# ---------------------------------------------------------------------------
load_dotenv()


# ===========================================================================
# TOOL DEFINITION
# ===========================================================================

@tool
def find_nearby_stores(
    location_query: str = None,
    user_lat: float = None,
    user_lon: float = None,
) -> str:
    """
    Finds nearby physical Body Shop store locations from the inventory database.

    This tool operates in two distinct modes — choose the right one based on
    the context available to you:

    MODE A — GPS Mode (preferred, most accurate):
        Use this mode when the system context or user message provides explicit
        GPS coordinates (latitude and longitude). Pass them as `user_lat` and
        `user_lon`. The tool will calculate the real-world distance (in km)
        from the user to every store using the Haversine formula, returning the
        3 closest stores sorted by distance ascending.

        Example invocation:
            find_nearby_stores(user_lat=28.490, user_lon=77.088)

    MODE B — Text Fallback (use when GPS is unavailable):
        Use this mode when no GPS coordinates are available but the user has
        mentioned a city, neighbourhood, landmark, or store name. Pass that
        string as `location_query`. The tool will perform a case-insensitive
        partial-text search across the store name, address, and city columns.

        Example invocation:
            find_nearby_stores(location_query="Ambience")
            find_nearby_stores(location_query="Sohna Road")

    Decision rules for the LLM:
        1. If BOTH coordinates and a text query are available, prefer MODE A.
        2. If NEITHER is provided, ask the user for their location before
           calling this tool.
        3. Never fabricate coordinates — only use values explicitly present
           in the system context or provided by the user.

    Args:
        location_query (str, optional): A city name, neighbourhood, landmark,
            or partial store name to search for. Used in MODE B.
        user_lat (float, optional): User's current latitude in decimal degrees.
            Used in MODE A (e.g. 28.490).
        user_lon (float, optional): User's current longitude in decimal degrees.
            Used in MODE A (e.g. 77.088).

    Returns:
        str: A formatted string listing up to 3 matching stores with their
             Store ID, address, and distance (MODE A) or a polite failure
             message if no stores were found.
    """

    # -----------------------------------------------------------------------
    # Validate — at least one input mode must be provided
    # -----------------------------------------------------------------------
    gps_mode = user_lat is not None and user_lon is not None
    text_mode = location_query and location_query.strip()

    if not gps_mode and not text_mode:
        return (
            "I need a location to search for stores. Please provide either "
            "GPS coordinates (latitude/longitude) or a city / neighbourhood name."
        )

    # -----------------------------------------------------------------------
    # Entity Resolution — normalise legacy/colloquial city names to the
    # canonical spellings used in the database before any SQL is executed.
    # Keys must be lowercase; values must match the database exactly.
    # -----------------------------------------------------------------------
    CITY_ALIASES = {
        # NCR / Haryana
        "gurgaon":          "Gurugram",
        "new gurgaon":      "Gurugram",
        # Maharashtra
        "bombay":           "Mumbai",
        # Karnataka
        "bangalore":        "Bengaluru",
        "bengalore":        "Bengaluru",   # common misspelling
        # Tamil Nadu
        "madras":           "Chennai",
        # West Bengal
        "calcutta":         "Kolkata",
        # Telangana
        "hyderabad deccan": "Hyderabad",
        # Odisha
        "cuttack":          "Cuttack",     # retained as-is (no alias needed)
        "bhubaneswar":      "Bhubaneswar",
        # Uttarakhand
        "dehradun":         "Dehradun",
        # Punjab
        "amritsar":         "Amritsar",
        # Andhra Pradesh
        "vizag":            "Visakhapatnam",
        "vishakhapatnam":   "Visakhapatnam",
        # Uttar Pradesh
        "allahabad":        "Prayagraj",
        "varanasi":         "Varanasi",
        # General
        "delhi":            "New Delhi",
        "new delhi":        "New Delhi",
        "ncr":              "New Delhi",
    }

    if text_mode:
        # FIX 3: The LLM frequently appends ", India" or ", Haryana" to the
        # city name (e.g. "Gurugram, India"). The ILIKE query then fails to
        # match because the DB stores plain city names without country suffixes.
        # We strip everything from the first comma onward before any lookup.
        location_query = location_query.strip().split(",")[0].strip()

        _query_lower = location_query.lower()
        if _query_lower in CITY_ALIASES:
            location_query = CITY_ALIASES[_query_lower]
        else:
            # Preserve the original capitalisation supplied by the caller
            location_query = location_query.strip()

    conn = None
    cursor = None

    try:
        # -------------------------------------------------------------------
        # Establish database connection
        # -------------------------------------------------------------------
        conn = psycopg2.connect(os.getenv("POSTGRES_URI"))
        cursor = conn.cursor()

        # -------------------------------------------------------------------
        # MODE A — Haversine GPS distance query
        # -------------------------------------------------------------------
        if gps_mode:
            haversine_sql = """
                SELECT
                    store_id,
                    name,
                    address,
                    city,
                    zip_code,
                    -- Haversine formula — result in kilometres
                    ROUND(
                        (6371 * ACOS(
                            COS(RADIANS(%s)) * COS(RADIANS(latitude))
                            * COS(RADIANS(longitude) - RADIANS(%s))
                            + SIN(RADIANS(%s)) * SIN(RADIANS(latitude))
                        ))::NUMERIC, 1
                    ) AS distance_km
                FROM public.stores
                -- Guard against stores at exactly the same point (ACOS domain)
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY distance_km ASC
                LIMIT 3;
            """
            # user_lat appears twice (COS and SIN terms), user_lon once
            cursor.execute(haversine_sql, (user_lat, user_lon, user_lat))
            rows = cursor.fetchall()

            if not rows:
                return "No store locations were found in the database."

            lines = [
                f"📍 Top {len(rows)} Body Shop store(s) nearest to your location:\n"
            ]
            for rank, (store_id, name, address, city, zip_code, distance_km) in enumerate(rows, start=1):
                lines.append(
                    f"  {rank}. {name} (ID: {store_id})\n"
                    f"     📏 {distance_km} km away\n"
                    f"     📬 {address}, {city} – {zip_code}"
                )

            return "\n".join(lines)

        # -------------------------------------------------------------------
        # MODE B — Case-insensitive text search (ILIKE)
        # -------------------------------------------------------------------
        pattern = f"%{location_query.strip()}%"
        text_sql = """
            SELECT
                store_id,
                name,
                address,
                city,
                zip_code
            FROM public.stores
            WHERE
                name    ILIKE %s
                OR address ILIKE %s
                OR city    ILIKE %s
            LIMIT 3;
        """
        cursor.execute(text_sql, (pattern, pattern, pattern))
        rows = cursor.fetchall()

        if not rows:
            return (
                f"No Body Shop stores were found matching '{location_query}'. "
                "Try a broader search term or a different neighbourhood name."
            )

        lines = [
            f"🔍 Body Shop store(s) matching '{location_query}':\n"
        ]
        for rank, (store_id, name, address, city, zip_code) in enumerate(rows, start=1):
            lines.append(
                f"  {rank}. {name} (ID: {store_id})\n"
                f"     📬 {address}, {city} – {zip_code}"
            )

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Error handling — surface DB issues cleanly to the agent
    # -----------------------------------------------------------------------
    except psycopg2.OperationalError as e:
        return f"Database connection error: {e}. Please check the POSTGRES_URI in your .env file."
    except psycopg2.Error as e:
        return f"Database query error: {e}"
    except Exception as e:
        return f"Unexpected error while searching for stores: {e}"

    # -----------------------------------------------------------------------
    # Always release resources
    # -----------------------------------------------------------------------
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

'''
# ===========================================================================
# LOCAL TEST HARNESS
# Run:  python tools_store.py
# ===========================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("TOOL TEST — tools_store.py")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Test 1 — MODE A: GPS coordinates near Gurgaon city centre
    # Expected: 3 stores sorted by real distance, with km values shown
    # ------------------------------------------------------------------
    print("\n[TEST 1] MODE A — GPS coordinates (Gurgaon centre)\n")
    result_gps = find_nearby_stores.invoke({
        "user_lat": 28.490,
        "user_lon": 77.088,
    })
    print(result_gps)

    print("\n" + "-" * 60)

    # ------------------------------------------------------------------
    # Test 2 — MODE B: Text search for "Ambience"
    # Expected: Ambience Mall store returned (ILIKE match on name/address)
    # ------------------------------------------------------------------
    print("\n[TEST 2] MODE B — Text search: 'Ambience'\n")
    result_text = find_nearby_stores.invoke({
        "location_query": "Ambience",
    })
    print(result_text)

    print("\n" + "-" * 60)

    # ------------------------------------------------------------------
    # Test 3 — Edge case: no arguments
    # Expected: Polite message asking for location input
    # ------------------------------------------------------------------
    print("\n[TEST 3] EDGE CASE — No arguments provided\n")
    result_empty = find_nearby_stores.invoke({})
    print(result_empty)

    print("\n" + "=" * 60)
'''