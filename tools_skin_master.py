# tools_skin_master.py
import os
import traceback
from dotenv import load_dotenv
from langchain_core.tools import tool
from gradio_client import Client

load_dotenv()
HF_TOKEN   = os.getenv("HUGGINGFACEHUB_API_TOKEN")
SPACE_ID   = "rohannsinghal/skin-master-api"


@tool
def consult_skin_master(query: str) -> str:
    """
    Expert dermatology and skincare consultation tool powered by the fine-tuned
    Skin Master SLM (rohannsinghal/skin-master-lora).

    The main agent MUST route to this tool whenever the user's message involves
    ANY of the following topics — even if only partially mentioned:

      • General skincare advice          (e.g. "how do I get clear skin")
      • Skin condition identification    (e.g. acne, rosacea, eczema, psoriasis,
                                          hyperpigmentation, melasma, dermatitis)
      • Dermatological treatment plans   (e.g. first-line treatments, OTC vs Rx)
      • Skincare routine building        (e.g. AM/PM routines, step ordering,
                                          layering products correctly)
      • Active ingredient guidance       (e.g. retinol, niacinamide, AHA/BHA,
                                          vitamin C, peptides, SPF)
      • Ingredient conflict checking     (e.g. "can I use retinol with vitamin C?",
                                          "does niacinamide clash with anything?")
      • Product recommendations          (e.g. best moisturiser for oily skin,
                                          cleanser for sensitive skin)
      • Skin type analysis               (e.g. oily, dry, combination, sensitive)
      • Sun protection advice            (e.g. SPF selection, reapplication)
      • Post-procedure skincare          (e.g. after peels, laser, microneedling)

    Do NOT attempt to answer skincare questions from general knowledge —
    always delegate to this tool to ensure medically-grounded, domain-expert
    responses from the fine-tuned model.

    Args:
        query: The user's skincare or dermatology question, passed verbatim.

    Returns:
        A detailed expert response string from the Skin Master SLM,
        or a graceful message if the Space is unavailable.
    """
    try:
        # Gradio client handles all version negotiation automatically —
        # no need to manually construct URLs or payloads.
        client = Client(SPACE_ID, token=HF_TOKEN)
        result   = client.predict(query, api_name="/ask")
        return result

    except Exception as e:
        print(f"[consult_skin_master] Space error:")
        traceback.print_exc()
        return (
            "The Skin Master dermatology expert is currently waking up from "
            "a cold start on the Hugging Face free tier. This typically takes "
            "20–30 seconds. Please try your question again in half a minute "
            "and the expert will be ready to help you. 🌿"
        )

'''
# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

    GREEN = "\033[92m"; RED = "\033[91m"
    CYAN  = "\033[96m"; RESET = "\033[0m"; BOLD = "\033[1m"

    print(f"\n{BOLD}{'='*65}{RESET}")
    print(f"{BOLD}  Skin Master — Space API Test{RESET}")
    print(f"{BOLD}{'='*65}{RESET}")
    print(f"  Space : {SPACE_ID}\n")

    TEST_CASES = [
        ("Acne Treatment",
         "What is the first-line treatment for mild acne vulgaris?",
         ["benzoyl peroxide","retinoid","salicylic","adapalene","tretinoin","topical"]),
        ("Ingredient Conflict",
         "Can I use niacinamide and vitamin C together?",
         ["niacinamide","vitamin c","together","layering","morning","separate"]),
        ("Routine Building",
         "Build me a simple AM routine for combination skin.",
         ["cleanser","moisturiser","moisturizer","spf","sunscreen","serum","routine"]),
        ("Condition Explanation",
         "What causes rosacea and what are its triggers?",
         ["rosacea","trigger","redness","flushing","vascular","sun"]),
    ]

    passed = 0
    for i, (name, query, keywords) in enumerate(TEST_CASES, start=1):
        print(f"{CYAN}{BOLD}Test {i}/{len(TEST_CASES)} — {name}{RESET}")
        print(f"  Query   : {query}")
        response = consult_skin_master.invoke({"query": query})
        print(f"  Response: {response.strip()}")
        hit      = any(kw.lower() in response.lower() for kw in keywords)
        print(f"  Result  : {GREEN}PASS ✔{RESET if hit else f'{RED}FAIL ✗{RESET}'}\n")
        passed  += hit

    print(f"{BOLD}{'='*65}{RESET}")
    print(f"{BOLD}  {passed}/{len(TEST_CASES)} passed{RESET}\n")
'''