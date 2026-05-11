import { Chip } from "@heroui/react";

import { emotionMeta } from "../../data/mockData.js";

export default function EmotionBars({ probabilities }) {
  const entries = Object.entries(probabilities).sort((a, b) => b[1] - a[1]);

  return (
    <div className="rounded-lg border border-border/70 bg-surface-secondary/60 p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">Distribucion emocional</p>
          <p className="text-xs text-muted">scores normalizados del modelo</p>
        </div>
        <Chip color="accent" size="sm" variant="soft">
          JSON visual
        </Chip>
      </div>

      <div className="space-y-4">
        {entries.map(([key, value]) => {
          const meta = emotionMeta[key] ?? emotionMeta.neutro;
          const percentage = Math.round(value * 100);

          return (
            <div key={key}>
              <div className="mb-1.5 flex items-center justify-between gap-3 text-sm">
                <span className="font-medium">{meta.label}</span>
                <span className="font-semibold">{percentage}%</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-surface-tertiary">
                <div
                  className={`metric-bar h-full rounded-full ${meta.riskClass}`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
