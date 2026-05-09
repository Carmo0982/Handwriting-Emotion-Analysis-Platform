from __future__ import annotations

import torch
from torch import nn

from ml.model import EmotionClassifier


def test_model_forward_pass_single_image_no_error(
    model: EmotionClassifier,
    single_input: torch.Tensor,
) -> None:
    with torch.no_grad():
        output = model(single_input)

    assert output.shape == (1, 4)


def test_model_forward_pass_batch_no_error(
    model: EmotionClassifier,
    batch_input: torch.Tensor,
) -> None:
    with torch.no_grad():
        output = model(batch_input)

    assert output.shape == (8, 4)


def test_model_output_shape_is_batch_by_4(
    model: EmotionClassifier,
    batch_input: torch.Tensor,
) -> None:
    with torch.no_grad():
        output = model(batch_input)

    assert output.shape == (batch_input.shape[0], 4)


def test_model_output_has_no_nan_values(
    model: EmotionClassifier,
    batch_input: torch.Tensor,
) -> None:
    with torch.no_grad():
        output = model(batch_input)

    assert not torch.isnan(output).any()


def test_model_output_has_no_inf_values(
    model: EmotionClassifier,
    batch_input: torch.Tensor,
) -> None:
    with torch.no_grad():
        output = model(batch_input)

    assert not torch.isinf(output).any()


def test_model_is_differentiable(
    model: EmotionClassifier,
    batch_input: torch.Tensor,
) -> None:
    model.train()
    targets = torch.tensor([0, 1, 2, 3, 0, 1, 2, 3])
    criterion = nn.CrossEntropyLoss()

    loss = criterion(model(batch_input), targets)
    loss.backward()

    assert any(parameter.grad is not None for parameter in model.parameters())


def test_model_parameters_are_updated_after_optimizer_step(
    model: EmotionClassifier,
    batch_input: torch.Tensor,
) -> None:
    model.train()
    targets = torch.tensor([0, 1, 2, 3, 0, 1, 2, 3])
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()
    before = model.classifier[-1].weight.detach().clone()

    loss = criterion(model(batch_input), targets)
    loss.backward()
    optimizer.step()

    after = model.classifier[-1].weight.detach()
    assert not torch.allclose(before, after)


def test_model_eval_mode_is_deterministic(
    model: EmotionClassifier,
    single_input: torch.Tensor,
) -> None:
    model.eval()

    with torch.no_grad():
        first_output = model(single_input)
        second_output = model(single_input)

    assert torch.allclose(first_output, second_output)


def test_model_train_mode_differs_from_eval_mode(
    model: EmotionClassifier,
    single_input: torch.Tensor,
) -> None:
    model.eval()
    with torch.no_grad():
        eval_output = model(single_input)

    model.train()
    torch.manual_seed(123)
    train_output = model(single_input)

    assert not torch.allclose(eval_output, train_output)


def test_model_works_without_gpu(
    model: EmotionClassifier,
    single_input: torch.Tensor,
) -> None:
    model.to("cpu")
    cpu_input = single_input.to("cpu")

    with torch.no_grad():
        output = model(cpu_input)

    assert output.device.type == "cpu"
    assert output.shape == (1, 4)
