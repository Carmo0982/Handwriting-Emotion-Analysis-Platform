from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import pytest
import torch
from PIL import Image, ImageDraw
from torch import nn

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.model import CLASS_NAMES, EmotionClassifier  # noqa: E402


@pytest.fixture()
def model() -> EmotionClassifier:
    torch.manual_seed(42)
    classifier = EmotionClassifier(
        pretrained=False,
        d_model=32,
        nhead=4,
        transformer_layers=1,
        dropout=0.3,
    )
    classifier.eval()
    return classifier


@pytest.fixture()
def single_input() -> torch.Tensor:
    torch.manual_seed(1)
    return torch.rand(1, 3, 224, 224)


@pytest.fixture()
def batch_input() -> torch.Tensor:
    torch.manual_seed(2)
    return torch.rand(8, 3, 224, 224)


@pytest.fixture()
def dummy_dataset_dir(tmp_path: Path) -> Path:
    for class_index, class_name in enumerate(CLASS_NAMES):
        class_dir = tmp_path / "data" / class_name
        class_dir.mkdir(parents=True)
        for image_index in range(5):
            image = Image.new(
                "RGB",
                (96, 96),
                color=(240 - class_index * 20, 240, 240),
            )
            draw = ImageDraw.Draw(image)
            y_position = 18 + image_index * 10
            draw.line((12, y_position, 84, y_position), fill=(0, 0, 0), width=2)
            image.save(class_dir / f"{class_name}_{image_index}.png")
    return tmp_path / "data"


@pytest.fixture()
def saved_model_path(tmp_path: Path) -> Path:
    model = TinyInferenceModel()
    model_path = tmp_path / "emotion_model.pt"
    torch.save({"model_state_dict": model.state_dict()}, model_path)
    return model_path


@pytest.fixture()
def white_image_bytes() -> bytes:
    image = Image.new("RGB", (224, 224), color=(255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture()
def corrupt_bytes() -> bytes:
    return b"this-is-not-an-image"


class TinyTrainingModel(nn.Module):
    def __init__(self, num_classes: int = 4) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Linear(3, num_classes),
        )

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        return self.network(images)


class TinyInferenceModel(nn.Module):
    def __init__(self, num_classes: int = 4, **_: object) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Linear(3, num_classes),
        )

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        return self.network(images)
