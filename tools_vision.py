# tools_vision.py
"""
LangGraph Agent Tool: AI-Powered Skin Type Classification via PyTorch Vision Model.

This module wraps the existing `SkinClassifier` PyTorch model from `vision.py`
into a LangChain-compatible `@tool`, enabling the LangGraph agent to analyze
user-uploaded images and detect skin type as part of a multi-step consultation
workflow.

Architecture Note:
    The `SkinClassifier` is instantiated once at module load time (outside the
    tool function). This is intentional — PyTorch model initialisation is
    expensive (loading weights, allocating memory). By initialising at import
    time, the model is warm and ready for every subsequent tool call without
    paying the cold-start cost on each invocation.
"""

import sys
from langchain_core.tools import tool

# --- Model Initialisation (Module-Level Singleton) ---
# Import the classifier class from the existing vision pipeline.
# This import triggers model weight loading exactly once when this module
# is first imported by the agent, not on every tool invocation.
from vision import SkinClassifier

# Instantiate the classifier as a module-level singleton. The LangGraph
# agent server imports this module once at startup, so this line executes
# exactly once per server lifecycle — keeping GPU/CPU memory usage stable
# and inference latency low for all subsequent calls.
classifier = SkinClassifier()


@tool
def analyze_uploaded_image(image_path: str) -> str:
    """
    Analyzes a user-uploaded photograph or selfie using a PyTorch deep learning
    model to detect and classify their skin type.

    CRITICAL INSTRUCTION — When to call this tool:
    If the system context or conversation history indicates that the user has
    uploaded an image, a photo, or a selfie, you MUST call this tool
    immediately and pass the provided file path as the `image_path` argument.
    Do NOT attempt to describe, interpret, or respond to an uploaded image
    without first calling this tool — you cannot see images directly. This
    tool is your only mechanism for extracting visual skin information.

    This tool must be called BEFORE any skin-type-specific product
    recommendations are made, as its output defines the user's skin profile
    that all subsequent recommendations should be grounded in.

    What this tool does:
    - Accepts a local file path pointing to the user's uploaded image.
    - Passes the image through a trained PyTorch skin classification model.
    - Returns a structured plain-text result containing the detected skin type
      and the model's confidence score.

    Skin types this model can detect:
    - Oily       — Excess sebum, enlarged pores, shine-prone T-zone.
    - Dry        — Tight, flaky, or rough texture, low moisture retention.
    - Combination — Oily T-zone with dry or normal cheeks.
    - Normal     — Balanced moisture, minimal blemishes, even texture.
    - Sensitive  — Prone to redness, irritation, or reactive to products.

    Correct usage pattern (follow this order strictly):
      Step 1 → User uploads image. System provides its file path.
      Step 2 → `analyze_uploaded_image("/path/to/uploaded/selfie.jpg")`
      Step 3 → Use the detected skin type to call `search_chroma_products`
                with a targeted query (e.g., "moisturiser for oily skin").
      Step 4 → Optionally call `check_sql_inventory` to verify stock.

    When NOT to call this tool:
    - If no image has been uploaded — do not fabricate or assume a file path.
    - If the user is asking a general skincare question without providing a photo.
    - If the skin type has already been detected earlier in the conversation
      and the user has not uploaded a new image.

    Args:
        image_path (str): The absolute or relative file path to the user's
                          uploaded image file. This path is provided by the
                          system or application layer when a file upload event
                          occurs. Supported formats depend on the underlying
                          `SkinClassifier` model (typically JPEG, PNG, WEBP).
                          Example: "/tmp/uploads/user_selfie_20240315.jpg"

    Returns:
        str: A plain-text sentence summarising the vision model's output.
             On success: "Vision Analysis Complete. Detected Skin Type:
                          {skin_type} (Confidence: {confidence})."
             On failure: A descriptive error string explaining what went wrong,
                         so the agent can inform the user and ask them to
                         re-upload or try a different image.
    """

    try:
        # --- 1. Run Inference ---
        # Delegate to the pre-loaded SkinClassifier singleton. The predict()
        # method handles all image preprocessing (resize, normalise, tensorise)
        # and returns a result dictionary. No model loading occurs here.
        prediction = classifier.predict(image_path)

        # --- 2. Validate Response Structure ---
        # Defensively check that predict() returned a dictionary, as any
        # unexpected return type should be caught early with a clear message
        # rather than producing a cryptic AttributeError downstream.
        if not isinstance(prediction, dict):
            return (
                f"Error: The vision model returned an unexpected response type "
                f"({type(prediction).__name__}). Expected a result dictionary. "
                f"Please contact support or try re-uploading the image."
            )

        # --- 3. Check for Model-Level Errors ---
        # CORRECTED SCHEMA: predict() does not return a "status" key.
        # Instead we check for the absence of "label" — the actual output key
        # confirmed from the SkinClassifier log: label='Oily', confidence=99.21%
        # If "label" is missing, something went wrong inside predict().
        if "label" not in prediction:
            error_message = prediction.get(
                "error",
                "An unspecified error occurred inside the vision model.",
            )
            return (
                f"Error: The skin analysis could not be completed. "
                f"Reason: {error_message} "
                f"Please ask the user to upload a clearer, well-lit photo "
                f"of their face and try again."
            )

        # --- 4. Extract Fields Using Confirmed Schema ---
        # "label" is the confirmed key from SkinClassifier's own log output.
        # "confidence" may be a float (99.21) or a string ("99.21%") depending
        # on the implementation — we normalise both cases into a display string.
        skin_type = prediction.get("label", "Unknown")
        raw_confidence = prediction.get("confidence", None)

        # Normalise confidence to a clean display string regardless of whether
        # predict() returns a float like 99.21 or a string like "99.21%".
        if raw_confidence is None:
            confidence_str = "N/A"
        elif isinstance(raw_confidence, str):
            # Already formatted — use as-is (e.g., "99.21%")
            confidence_str = raw_confidence
        else:
            # Float or int — format to 2 decimal places and append % symbol
            confidence_str = f"{raw_confidence:.2f}%"

        return (
            f"Vision Analysis Complete. "
            f"Detected Skin Type: {skin_type} (Confidence: {confidence_str})."
        )

    except FileNotFoundError:
        # Raised when the image_path points to a file that does not exist.
        # This typically means the upload handler failed or passed a wrong path.
        return (
            f"Error: The image file could not be found at the path provided: "
            f"'{image_path}'. The file may not have uploaded correctly. "
            f"Please ask the user to try uploading their photo again."
        )

    except Exception as e:
        # Catch-all for any unexpected failures during inference (e.g., corrupt
        # image file, GPU out-of-memory, unsupported image format). Always
        # returns a string so the agent workflow is never interrupted by an
        # unhandled exception from within the tool.
        return (
            f"Error: An unexpected error occurred during skin image analysis "
            f"for file '{image_path}'. "
            f"Technical details: {str(e)}"
        )

'''
# ---------------------------------------------------------------------------
# Local Test Block
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    test_image = sys.argv[1] if len(sys.argv) > 1 else "/Users/admin/omnichannel-agent/test_face.jpg"

    print("=" * 50)
    print("  tools_vision.py — Local Test")
    print("=" * 50)
    print(f"\n[TEST] Analyzing image: '{test_image}'")

    result = analyze_uploaded_image.invoke({"image_path": test_image})
    print(f"[RESULT] {result}")
    print("=" * 50)

    # Documenting the root cause analysis for the fix
    print("\n" + "=" * 50)
    print("  Root Cause Analysis")
    print("=" * 50)
'''