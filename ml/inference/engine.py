from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import torch
from PIL import Image

from ml.model import CLASS_NAMES, EmotionClassifier
from ml.training.augmentation import get_inference_transforms


class InferenceEngine:
    def __init__(
        self,
        model_path: str | Path,
        device: str = "cpu",
    ) -> None:
        self.device = self._resolve_device(device)
        self.class_names = CLASS_NAMES
        self.transforms = get_inference_transforms()
        self.model = EmotionClassifier(
            num_classes=len(self.class_names),
            pretrained=False,
        )
        self._load_checkpoint(model_path)
        self.model.to(self.device)
        self.model.eval()

    def predict(self, image_bytes: bytes) -> dict[str, Any]:
        image = self._load_image(image_bytes)
        tensor = self.transforms(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            probabilities = torch.softmax(logits, dim=1).squeeze(0).cpu()

        scores = {
            class_name: float(probabilities[index].item())
            for index, class_name in enumerate(self.class_names)
        }
        predicted_index = int(torch.argmax(probabilities).item())
        emotion = self.class_names[predicted_index]

        return {
            "emotion": emotion,
            "confidence": scores[emotion],
            "scores": scores,
        }

    def _load_checkpoint(self, model_path: str | Path) -> None:
        checkpoint = torch.load(Path(model_path), map_location=self.device)
        state_dict = self._extract_state_dict(checkpoint)
        self.model.load_state_dict(state_dict)

    def _extract_state_dict(self, checkpoint: Any) -> dict[str, torch.Tensor]:
        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            return checkpoint["model_state_dict"]
        if isinstance(checkpoint, dict):
            return checkpoint
        raise ValueError("Unsupported checkpoint format")

    def _load_image(self, image_bytes: bytes) -> Image.Image:
        try:
            return Image.open(BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            raise ValueError("Could not decode image bytes") from exc

    def _resolve_device(self, device: Optional[str]) -> torch.device:
        requested_device = torch.device(device or "cpu")
        if requested_device.type == "cuda" and not torch.cuda.is_available():
            return torch.device("cpu")
        return requested_device
