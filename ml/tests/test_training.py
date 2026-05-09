from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from conftest import TinyTrainingModel
from ml.training.dataset import HandwritingDataset
from ml.training.train import run_kfold_training, train_fold


def tiny_model_factory() -> TinyTrainingModel:
    torch.manual_seed(123)
    return TinyTrainingModel()


def test_train_fold_runs_without_error(
    dummy_dataset_dir: Path,
    tmp_path: Path,
) -> None:
    dataset = HandwritingDataset(dummy_dataset_dir)

    result = train_fold(
        dataset=dataset,
        train_indices=np.arange(12),
        val_indices=np.arange(12, 20),
        epochs=1,
        batch_size=4,
        checkpoint_dir=tmp_path,
        device="cpu",
        model_factory=tiny_model_factory,
    )

    assert result["fold"] == 1


def test_train_fold_returns_weights_and_f1_score(
    dummy_dataset_dir: Path,
    tmp_path: Path,
) -> None:
    dataset = HandwritingDataset(dummy_dataset_dir)

    result = train_fold(
        dataset=dataset,
        train_indices=np.arange(12),
        val_indices=np.arange(12, 20),
        epochs=1,
        batch_size=4,
        checkpoint_dir=tmp_path,
        device="cpu",
        model_factory=tiny_model_factory,
    )

    assert "model_state_dict" in result
    assert "f1_score" in result


def test_train_fold_f1_score_is_between_0_and_1(
    dummy_dataset_dir: Path,
    tmp_path: Path,
) -> None:
    dataset = HandwritingDataset(dummy_dataset_dir)

    result = train_fold(
        dataset=dataset,
        train_indices=np.arange(12),
        val_indices=np.arange(12, 20),
        epochs=1,
        batch_size=4,
        checkpoint_dir=tmp_path,
        device="cpu",
        model_factory=tiny_model_factory,
    )

    assert 0.0 <= result["f1_score"] <= 1.0


def test_train_fold_saves_checkpoint_file(
    dummy_dataset_dir: Path,
    tmp_path: Path,
) -> None:
    dataset = HandwritingDataset(dummy_dataset_dir)

    result = train_fold(
        dataset=dataset,
        train_indices=np.arange(12),
        val_indices=np.arange(12, 20),
        epochs=1,
        batch_size=4,
        checkpoint_dir=tmp_path,
        device="cpu",
        model_factory=tiny_model_factory,
    )

    assert Path(result["checkpoint_path"]).exists()


def test_kfold_training_runs_k_folds(
    dummy_dataset_dir: Path,
    tmp_path: Path,
) -> None:
    dataset = HandwritingDataset(dummy_dataset_dir)

    result = run_kfold_training(
        dataset=dataset,
        k=2,
        epochs=1,
        batch_size=4,
        checkpoint_dir=tmp_path,
        device="cpu",
        num_workers=0,
        model_factory=tiny_model_factory,
    )

    assert len(result["folds"]) == 2


def test_kfold_training_returns_k_scores(
    dummy_dataset_dir: Path,
    tmp_path: Path,
) -> None:
    dataset = HandwritingDataset(dummy_dataset_dir)

    result = run_kfold_training(
        dataset=dataset,
        k=2,
        epochs=1,
        batch_size=4,
        checkpoint_dir=tmp_path,
        device="cpu",
        num_workers=0,
        model_factory=tiny_model_factory,
    )

    scores = [fold["best_f1_macro"] for fold in result["folds"]]
    assert len(scores) == 2
    assert all(0.0 <= score <= 1.0 for score in scores)
