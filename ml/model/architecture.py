from __future__ import annotations

from typing import Sequence

import timm
import torch
from torch import nn


CLASS_NAMES: tuple[str, str, str, str] = (
    "neutral",
    "anxiety",
    "stress",
    "depression",
)


class EmotionClassifier(nn.Module):
    def __init__(
        self,
        num_classes: int = 4,
        pretrained: bool = True,
        d_model: int = 1280,
        nhead: int = 8,
        transformer_layers: int = 4,
        dropout: float = 0.3,
        class_names: Sequence[str] = CLASS_NAMES,
    ) -> None:
        super().__init__()
        if num_classes != len(class_names):
            raise ValueError("num_classes must match class_names length")

        self.num_classes = num_classes
        self.class_names = tuple(class_names)
        self.d_model = d_model
        self.patch_count = 49

        self.backbone = timm.create_model(
            "efficientnet_b0",
            pretrained=pretrained,
            features_only=True,
        )
        backbone_channels = self.backbone.feature_info.channels()[-1]
        self.channel_projection: nn.Module
        if backbone_channels == d_model:
            self.channel_projection = nn.Identity()
        else:
            self.channel_projection = nn.Conv2d(
                backbone_channels,
                d_model,
                kernel_size=1,
            )

        self.patch_projection = nn.AdaptiveAvgPool2d((7, 7))
        self.patch_flatten = nn.Flatten(start_dim=2)
        self.position_embedding = nn.Parameter(torch.zeros(1, self.patch_count, d_model))

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=0.1,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=transformer_layers,
        )

        self.classifier = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, 256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, num_classes),
        )

        self._init_parameters()

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        tokens = self.extract_patch_tokens(images)
        encoded_tokens = self.transformer_encoder(tokens)
        representation = encoded_tokens.mean(dim=1)
        return self.classifier(representation)

    def extract_patch_tokens(self, images: torch.Tensor) -> torch.Tensor:
        feature_map = self.backbone(images)[-1]
        feature_map = self.channel_projection(feature_map)
        pooled_features = self.patch_projection(feature_map)
        tokens = self.patch_flatten(pooled_features).transpose(1, 2)
        return tokens + self.position_embedding

    def _init_parameters(self) -> None:
        nn.init.trunc_normal_(self.position_embedding, std=0.02)
        for module in self.classifier:
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
