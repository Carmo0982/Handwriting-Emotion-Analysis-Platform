from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
from sklearn.model_selection import StratifiedKFold
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, Dataset, Subset

from ml.model import CLASS_NAMES, EmotionClassifier
from ml.training.augmentation import get_base_transforms, get_train_transforms
from ml.training.dataset import HandwritingDataset
from ml.training.evaluate import evaluate_model


logger = logging.getLogger(__name__)


def run_kfold_training(
    dataset: Dataset,
    k: int = 5,
    epochs: int = 10,
    batch_size: int = 16,
    checkpoint_dir: str | Path = "checkpoints",
    device: Optional[str | torch.device] = None,
    num_workers: int = 2,
    seed: int = 42,
    model_factory: Optional[Callable[[], nn.Module]] = None,
) -> dict[str, Any]:
    resolved_device = _resolve_device(device)
    output_dir = Path(checkpoint_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    labels = _extract_labels(dataset)
    splitter = StratifiedKFold(n_splits=k, shuffle=True, random_state=seed)
    fold_results: list[dict[str, Any]] = []

    for fold_index, (train_indices, val_indices) in enumerate(
        splitter.split(np.zeros(len(labels)), labels),
        start=1,
    ):
        fold_result = train_fold(
            dataset=dataset,
            train_indices=train_indices,
            val_indices=val_indices,
            fold_index=fold_index,
            epochs=epochs,
            batch_size=batch_size,
            checkpoint_dir=output_dir,
            device=resolved_device,
            num_workers=num_workers,
            model_factory=model_factory,
        )
        fold_results.append(fold_result)
        logger.info(
            "Fold %s completed - best macro F1 %.4f",
            fold_index,
            fold_result["best_f1_macro"],
        )

    mean_f1 = float(np.mean([fold["best_f1_macro"] for fold in fold_results]))
    logger.info("K-Fold training completed - mean macro F1 %.4f", mean_f1)

    return {
        "folds": fold_results,
        "mean_f1_macro": mean_f1,
    }


def train_fold(
    dataset: Dataset,
    train_indices: np.ndarray,
    val_indices: np.ndarray,
    fold_index: int = 1,
    epochs: int = 1,
    batch_size: int = 16,
    checkpoint_dir: str | Path = "checkpoints",
    device: Optional[str | torch.device] = None,
    num_workers: int = 0,
    model_factory: Optional[Callable[[], nn.Module]] = None,
) -> dict[str, Any]:
    resolved_device = _resolve_device(device)
    output_dir = Path(checkpoint_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_subset, val_subset = _build_fold_subsets(
        dataset=dataset,
        train_indices=np.asarray(train_indices),
        val_indices=np.asarray(val_indices),
    )
    train_loader = DataLoader(
        train_subset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=resolved_device.type == "cuda",
    )
    val_loader = DataLoader(
        val_subset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=resolved_device.type == "cuda",
    )

    model = model_factory() if model_factory is not None else EmotionClassifier(
        num_classes=len(CLASS_NAMES),
        pretrained=True,
    )
    model.to(resolved_device)

    criterion = nn.CrossEntropyLoss()
    optimizer = AdamW(model.parameters(), lr=1e-4, weight_decay=1e-2)
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs)

    best_f1 = -1.0
    best_metrics: dict[str, Any] = {}
    best_checkpoint_path = output_dir / f"fold_{fold_index}_best.pt"

    for epoch in range(1, epochs + 1):
        train_loss = _train_one_epoch(
            model=model,
            dataloader=train_loader,
            criterion=criterion,
            optimizer=optimizer,
            device=resolved_device,
        )
        scheduler.step()

        metrics = evaluate_model(
            model=model,
            dataloader=val_loader,
            device=resolved_device,
            class_names=CLASS_NAMES,
        )
        f1_macro = float(metrics["f1_macro"])

        logger.info(
            "Fold %s epoch %s/%s - loss %.4f - macro F1 %.4f",
            fold_index,
            epoch,
            epochs,
            train_loss,
            f1_macro,
        )

        if f1_macro > best_f1:
            best_f1 = f1_macro
            best_metrics = metrics
            torch.save(
                {
                    "fold": fold_index,
                    "epoch": epoch,
                    "f1_macro": best_f1,
                    "class_names": CLASS_NAMES,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                },
                best_checkpoint_path,
            )

    return {
        "fold": fold_index,
        "best_f1_macro": best_f1,
        "f1_score": best_f1,
        "metrics": best_metrics,
        "model_state_dict": model.state_dict(),
        "checkpoint_path": str(best_checkpoint_path),
    }


def _train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    model.train()
    total_loss = 0.0
    total_samples = 0

    for images, labels in dataloader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad(set_to_none=True)
        logits = model(images)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()

        batch_size = int(images.size(0))
        total_loss += float(loss.item()) * batch_size
        total_samples += batch_size

    if total_samples == 0:
        raise ValueError("Cannot train on an empty dataloader")
    return total_loss / total_samples


def _build_fold_subsets(
    dataset: Dataset,
    train_indices: np.ndarray,
    val_indices: np.ndarray,
) -> tuple[Subset, Subset]:
    if isinstance(dataset, HandwritingDataset):
        train_dataset = dataset.with_transform(get_train_transforms())
        val_dataset = dataset.with_transform(get_base_transforms())
    else:
        train_dataset = dataset
        val_dataset = dataset

    return (
        Subset(train_dataset, train_indices.tolist()),
        Subset(val_dataset, val_indices.tolist()),
    )


def _extract_labels(dataset: Dataset) -> np.ndarray:
    if hasattr(dataset, "targets"):
        return np.asarray(getattr(dataset, "targets"), dtype=np.int64)
    return np.asarray([int(dataset[index][1]) for index in range(len(dataset))])


def _resolve_device(device: Optional[str | torch.device]) -> torch.device:
    if device is not None:
        requested_device = torch.device(device)
        if requested_device.type == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA requested but unavailable; falling back to CPU")
            return torch.device("cpu")
        return requested_device
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().tolist()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {
            str(key): _json_safe(child)
            for key, child in value.items()
            if key != "model_state_dict"
        }
    if isinstance(value, list):
        return [_json_safe(child) for child in value]
    if isinstance(value, tuple):
        return [_json_safe(child) for child in value]
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the TDSE emotion classifier.")
    parser.add_argument("--data-dir", required=True, help="Dataset root directory.")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs.")
    parser.add_argument("--k-folds", type=int, default=5, help="Number of K-Folds.")
    parser.add_argument(
        "--checkpoint-dir",
        default="checkpoints",
        help="Directory for fold checkpoints.",
    )
    parser.add_argument(
        "--metrics-output",
        default="training_metrics.json",
        help="Path where JSON metrics will be written.",
    )
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size.")
    parser.add_argument(
        "--num-workers",
        type=int,
        default=2,
        help="DataLoader worker count.",
    )
    parser.add_argument("--device", default=None, help="Torch device, e.g. cpu or cuda.")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()

    dataset = HandwritingDataset(args.data_dir)
    if len(dataset) == 0:
        raise ValueError(f"No training samples found in {args.data_dir}")

    result = run_kfold_training(
        dataset=dataset,
        k=args.k_folds,
        epochs=args.epochs,
        batch_size=args.batch_size,
        checkpoint_dir=args.checkpoint_dir,
        device=args.device,
        num_workers=args.num_workers,
    )

    metrics_path = Path(args.metrics_output)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps(_json_safe(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    logger.info("Training metrics written to %s", metrics_path)


if __name__ == "__main__":
    main()
