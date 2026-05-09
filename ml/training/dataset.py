from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Optional

from PIL import Image
from torch import Tensor
from torch.utils.data import Dataset

from ml.model import CLASS_NAMES
from ml.training.augmentation import get_base_transforms, get_train_transforms


SUPPORTED_IMAGE_EXTENSIONS: tuple[str, ...] = (
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
)


class HandwritingDataset(Dataset):
    def __init__(
        self,
        root_dir: str | Path,
        transform: Optional[Callable[[Image.Image], Tensor]] = None,
        augment: bool = False,
        class_names: Sequence[str] = CLASS_NAMES,
        samples: Optional[list[tuple[Path, int]]] = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.class_names = tuple(class_names)
        self.class_to_idx = {
            class_name: index for index, class_name in enumerate(self.class_names)
        }
        self.transform = transform or (
            get_train_transforms() if augment else get_base_transforms()
        )
        self.samples = samples if samples is not None else self._discover_samples()
        self.targets = [label for _, label in self.samples]

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[Tensor, int]:
        image_path, label = self.samples[index]
        with Image.open(image_path) as image:
            transformed_image = self.transform(image.convert("RGB"))
        return transformed_image, label

    def with_transform(
        self,
        transform: Callable[[Image.Image], Tensor],
    ) -> "HandwritingDataset":
        return HandwritingDataset(
            root_dir=self.root_dir,
            transform=transform,
            class_names=self.class_names,
            samples=self.samples,
        )

    def _discover_samples(self) -> list[tuple[Path, int]]:
        samples: list[tuple[Path, int]] = []
        for class_name, label in self.class_to_idx.items():
            class_dir = self.root_dir / class_name
            if not class_dir.exists():
                continue
            class_files = [
                path
                for path in class_dir.rglob("*")
                if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
            ]
            samples.extend((path, label) for path in sorted(class_files))
        return samples
