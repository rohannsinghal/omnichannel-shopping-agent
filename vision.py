"""
vision.py — Production-grade inference wrapper for a TorchScript skin classifier.

Usage:
    python vision.py                        # runs built-in smoke test on test_face.jpg
    python vision.py --image path/to/img    # run on a custom image
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict
import torchvision.models as models
import torch.nn as nn
import torch
import torch.nn.functional as F
from PIL import Image, UnidentifiedImageError
from torchvision import transforms

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SkinClassifier")


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------
class SkinClassifier:
    """
    Inference wrapper around a TorchScript-traced skin-type classification model.

    Attributes:
        MODEL_PATH  : Path to the .pth TorchScript file.
        CLASSES     : Ordered list of class labels matching the model's output logits.
        device      : torch.device selected at initialisation (MPS → CPU fallback).
        model       : Loaded, eval-mode TorchScript module.
        transform   : Composed torchvision preprocessing pipeline.
    """

    MODEL_PATH: str = "best_skin_model.pth"

    CLASSES: list[str] = [
        "Combination",
        "Dry",
        "Normal",
        "Oily",
        "Sensitive",
    ]

    # ImageNet statistics
    _IMAGENET_MEAN = [0.485, 0.456, 0.406]
    _IMAGENET_STD  = [0.229, 0.224, 0.225]

    def __init__(self, model_path: str | None = None) -> None:
        """
        Load and prepare the TorchScript model.

        Args:
            model_path: Override for the default MODEL_PATH constant.

        Raises:
            FileNotFoundError : Model file does not exist at the given path.
            RuntimeError      : TorchScript load failure (corrupt / incompatible file).
        """
        resolved_path = Path(model_path or self.MODEL_PATH)
        if not resolved_path.is_file():
            raise FileNotFoundError(
                f"Model file not found: '{resolved_path.resolve()}'. "
                "Ensure 'best_skin_model.pth' is in the working directory."
            )

        # ── Device selection ────────────────────────────────────────────────
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")
        logger.info("Using device: %s", self.device)

        # ── Model loading ────────────────────────────────────────────────────
        try:
            # 1. Recreate the exact architecture used during training
            # Since you used MobileNetV2 for 5 classes (Combination, Dry, Normal, Oily, Sensitive)
            self.model = models.mobilenet_v2(weights=None)
            num_ftrs = self.model.classifier[1].in_features
            self.model.classifier[1] = nn.Linear(num_ftrs, 5) 

            # 2. Load the checkpoint dictionary
            checkpoint = torch.load(resolved_path, map_location=self.device)
            
            # 3. Extract the weights specifically from 'model_state_dict'
            if 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
                self.classes = checkpoint.get('class_names', ['Combination', 'Dry', 'Normal', 'Oily', 'Sensitive'])
                logger.info("Weights extracted from checkpoint['model_state_dict']")
            else:
                # Fallback in case you ever use a file that is ONLY weights
                self.model.load_state_dict(checkpoint)

        except Exception as exc:
            raise RuntimeError(
                f"Failed to initialize or load model from '{resolved_path}': {exc}"
            ) from exc

        self.model.to(self.device)
        self.model.eval()
        logger.info(f"Model loaded onto {self.device} and set to eval mode.")

        # ── Preprocessing pipeline ───────────────────────────────────────────
        self.transform = transforms.Compose(
            [
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=self._IMAGENET_MEAN,
                    std=self._IMAGENET_STD,
                ),
            ]
        )
        logger.info("Transform pipeline initialised (Resize→CenterCrop→ToTensor→Normalize).")

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #
    def predict(self, image_path: str) -> Dict[str, object]:
        """
        Run inference on a single image and return a structured result dict.

        Args:
            image_path: Absolute or relative path to a JPEG / PNG image.

        Returns:
            A dict with the shape::

                {
                    "label":      "Oily",          # predicted class string
                    "confidence": 94.73,           # softmax probability × 100
                    "all_scores": {                # full probability distribution
                        "Combination": 1.42,
                        "Dry":         0.61,
                        "Normal":      2.18,
                        "Oily":       94.73,
                        "Sensitive":   1.06,
                    },
                    "image_path": "/abs/path/to/img.jpg",
                }

        Raises:
            FileNotFoundError    : Image file not found.
            UnidentifiedImageError: Pillow cannot decode the file.
            ValueError           : Image conversion to RGB fails.
            RuntimeError         : Model inference failure.
        """
        img_path = Path(image_path)
        if not img_path.is_file():
            raise FileNotFoundError(f"Image not found: '{img_path.resolve()}'")

        # ── Load & convert ───────────────────────────────────────────────────
        try:
            image = Image.open(img_path).convert("RGB")
        except UnidentifiedImageError as exc:
            raise UnidentifiedImageError(
                f"Pillow could not identify '{img_path}' as a valid image file."
            ) from exc
        except Exception as exc:
            raise ValueError(f"Failed to open image '{img_path}': {exc}") from exc

        # ── Preprocess ───────────────────────────────────────────────────────
        tensor: torch.Tensor = self.transform(image)   # (C, H, W)
        tensor = tensor.unsqueeze(0).to(self.device)   # (1, C, H, W)

        # ── Inference ────────────────────────────────────────────────────────
        try:
            with torch.no_grad():
                logits: torch.Tensor = self.model(tensor)   # (1, num_classes)
        except Exception as exc:
            raise RuntimeError(f"Model inference failed: {exc}") from exc

        # ── Post-process ─────────────────────────────────────────────────────
        probabilities: torch.Tensor = F.softmax(logits, dim=1).squeeze(0)  # (num_classes,)
        probs_list = probabilities.cpu().tolist()

        predicted_idx: int = int(torch.argmax(probabilities).item())
        predicted_label: str = self.CLASSES[predicted_idx]
        confidence: float = round(probs_list[predicted_idx] * 100, 2)

        all_scores: Dict[str, float] = {
            cls: round(prob * 100, 2)
            for cls, prob in zip(self.CLASSES, probs_list)
        }

        result = {
            "label":      predicted_label,
            "confidence": confidence,
            "all_scores": all_scores,
            "image_path": str(img_path.resolve()),
        }

        logger.info(
            "Prediction → label='%s', confidence=%.2f%%", predicted_label, confidence
        )
        return result

'''
# ---------------------------------------------------------------------------
# CLI / smoke-test entry-point
# ---------------------------------------------------------------------------
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SkinClassifier — local inference test",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--image",
        default="test_face.jpg",
        help="Path to the test image (JPEG or PNG).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override path to the TorchScript model file.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    print("\n" + "=" * 60)
    print("  SkinClassifier — Local Inference Test")
    print("=" * 60)

    # ── Initialise classifier ────────────────────────────────────────────────
    try:
        classifier = SkinClassifier(model_path=args.model)
    except FileNotFoundError as e:
        logger.error("Model load failed: %s", e)
        sys.exit(1)
    except RuntimeError as e:
        logger.error("Runtime error during model load: %s", e)
        sys.exit(1)

    # ── Run prediction ───────────────────────────────────────────────────────
    try:
        result = classifier.predict(args.image)
    except FileNotFoundError as e:
        logger.error("Image not found: %s", e)
        sys.exit(1)
    except (UnidentifiedImageError, ValueError) as e:
        logger.error("Image loading error: %s", e)
        sys.exit(1)
    except RuntimeError as e:
        logger.error("Inference error: %s", e)
        sys.exit(1)

    # ── Pretty-print result ──────────────────────────────────────────────────
    print(f"\n  Image       : {result['image_path']}")
    print(f"  Prediction  : {result['label']}")
    print(f"  Confidence  : {result['confidence']}%")
    print("\n  Full probability distribution:")
    for cls, score in sorted(result["all_scores"].items(), key=lambda x: -x[1]):
        bar = "█" * int(score / 5)
        print(f"    {cls:<12} {score:>6.2f}%  {bar}")
    print("\n  Raw JSON output:")
    print(json.dumps(result, indent=4))
    print("=" * 60 + "\n")
'''