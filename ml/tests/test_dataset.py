from __future__ import annotations

from pathlib import Path

from PIL import Image
import torch

from ml.model import CLASS_NAMES
from ml.training.dataset import HandwritingDataset


def test_dataset_loads_images_from_directory(dummy_dataset_dir: Path) -> None:
    dataset = HandwritingDataset(dummy_dataset_dir)

    assert len(dataset.samples) > 0


def test_dataset_length_matches_total_images(dummy_dataset_dir: Path) -> None:
    dataset = HandwritingDataset(dummy_dataset_dir)

    assert len(dataset) == 20


def test_dataset_returns_tensor_and_label(dummy_dataset_dir: Path) -> None:
    dataset = HandwritingDataset(dummy_dataset_dir)

    tensor, label = dataset[0]

    assert isinstance(tensor, torch.Tensor)
    assert isinstance(label, int)


def test_dataset_tensor_shape_is_3x224x224(dummy_dataset_dir: Path) -> None:
    dataset = HandwritingDataset(dummy_dataset_dir)

    tensor, _ = dataset[0]

    assert tensor.shape == (3, 224, 224)


def test_dataset_tensor_values_are_normalized(dummy_dataset_dir: Path) -> None:
    dataset = HandwritingDataset(dummy_dataset_dir)

    tensor, _ = dataset[0]

    assert torch.isfinite(tensor).all()
    assert tensor.min() >= -3.0
    assert tensor.max() <= 3.0


def test_dataset_labels_are_in_range_0_to_3(dummy_dataset_dir: Path) -> None:
    dataset = HandwritingDataset(dummy_dataset_dir)
    labels = [dataset[index][1] for index in range(len(dataset))]

    assert all(0 <= label <= 3 for label in labels)


def test_dataset_with_augmentation_returns_valid_tensor(dummy_dataset_dir: Path) -> None:
    dataset = HandwritingDataset(dummy_dataset_dir, augment=True)

    tensor, label = dataset[0]

    assert tensor.shape == (3, 224, 224)
    assert torch.isfinite(tensor).all()
    assert 0 <= label <= 3


def test_dataset_empty_directory_returns_length_zero(tmp_path: Path) -> None:
    dataset = HandwritingDataset(tmp_path)

    assert len(dataset) == 0


def test_dataset_missing_class_folder_does_not_raise(tmp_path: Path) -> None:
    neutral_dir = tmp_path / "neutral"
    neutral_dir.mkdir()
    Image.new("RGB", (32, 32), color=(255, 255, 255)).save(neutral_dir / "sample.png")

    dataset = HandwritingDataset(tmp_path, class_names=CLASS_NAMES)

    assert len(dataset) == 1
    assert dataset[0][1] == 0
