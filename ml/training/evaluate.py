from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence

import matplotlib.pyplot as plt
import numpy as np
import torch
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from torch import nn
from torch.utils.data import DataLoader

from ml.model import CLASS_NAMES


def evaluate_model(
    model: nn.Module,
    dataloader: DataLoader,
    device: Optional[str | torch.device] = None,
    class_names: Sequence[str] = CLASS_NAMES,
) -> dict[str, Any]:
    resolved_device = _resolve_device(model, device)
    model.to(resolved_device)
    model.eval()

    all_predictions: list[int] = []
    all_labels: list[int] = []

    with torch.no_grad():
        for images, labels in dataloader:
            images = images.to(resolved_device)
            labels = labels.to(resolved_device)
            logits = model(images)
            predictions = torch.argmax(logits, dim=1)

            all_predictions.extend(predictions.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    if not all_labels:
        raise ValueError("Cannot evaluate on an empty dataloader")

    label_ids = list(range(len(class_names)))
    f1_values = f1_score(
        all_labels,
        all_predictions,
        labels=label_ids,
        average=None,
        zero_division=0,
    )
    matrix = confusion_matrix(all_labels, all_predictions, labels=label_ids)

    return {
        "accuracy": float(accuracy_score(all_labels, all_predictions)),
        "f1_macro": float(
            f1_score(
                all_labels,
                all_predictions,
                labels=label_ids,
                average="macro",
                zero_division=0,
            )
        ),
        "f1_per_class": {
            class_name: float(f1_values[index])
            for index, class_name in enumerate(class_names)
        },
        "confusion_matrix": matrix,
    }


def plot_confusion_matrix(
    cm: np.ndarray,
    output_path: str | Path = "confusion_matrix.png",
    class_names: Sequence[str] = CLASS_NAMES,
) -> str:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    figure, axis = plt.subplots(figsize=(7, 6))
    image = axis.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    figure.colorbar(image, ax=axis)

    axis.set(
        xticks=np.arange(len(class_names)),
        yticks=np.arange(len(class_names)),
        xticklabels=class_names,
        yticklabels=class_names,
        ylabel="True label",
        xlabel="Predicted label",
        title="Confusion Matrix",
    )
    plt.setp(axis.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    threshold = cm.max() / 2.0 if cm.size else 0.0
    for row_index in range(cm.shape[0]):
        for column_index in range(cm.shape[1]):
            axis.text(
                column_index,
                row_index,
                format(cm[row_index, column_index], "d"),
                ha="center",
                va="center",
                color="white" if cm[row_index, column_index] > threshold else "black",
            )

    figure.tight_layout()
    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return str(output)


def _resolve_device(
    model: nn.Module,
    device: Optional[str | torch.device],
) -> torch.device:
    if device is not None:
        return torch.device(device)
    try:
        return next(model.parameters()).device
    except StopIteration:
        return torch.device("cpu")
