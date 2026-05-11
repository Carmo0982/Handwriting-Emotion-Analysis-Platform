import { biomarkerLabels } from "../../data/mockData.js";

const order = ["pressure", "rhythm", "slant", "spacing", "strokeVariability"];

export default function BiomarkerRadar({ biomarkers }) {
  const center = 110;
  const radius = 70;
  const points = order.map((key, index) =>
    polarPoint(center, center, radius * biomarkers[key], index, order.length),
  );
  const gridRings = [0.25, 0.5, 0.75, 1];
  const polygon = points.map((point) => `${point.x},${point.y}`).join(" ");

  return (
    <div className="rounded-lg border border-border/70 bg-surface-secondary/60 p-4">
      <div className="mb-4">
        <p className="text-sm font-semibold">Biomarcadores graficos</p>
        <p className="text-xs text-muted">presion, ritmo y rasgos del trazo</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-[220px_1fr]">
        <svg
          aria-label="Radar de biomarcadores"
          className="mx-auto h-[220px] w-[220px]"
          role="img"
          viewBox="0 0 220 220"
        >
          {gridRings.map((ring) => (
            <polygon
              className="fill-none stroke-border"
              key={ring}
              points={order
                .map((_, index) =>
                  polarPoint(center, center, radius * ring, index, order.length),
                )
                .map((point) => `${point.x},${point.y}`)
                .join(" ")}
              strokeWidth="1"
            />
          ))}

          {order.map((key, index) => {
            const edge = polarPoint(center, center, radius, index, order.length);
            const label = polarPoint(center, center, radius + 24, index, order.length);

            return (
              <g key={key}>
                <line
                  className="stroke-border"
                  strokeWidth="1"
                  x1={center}
                  x2={edge.x}
                  y1={center}
                  y2={edge.y}
                />
                <text
                  className="fill-muted text-[9px] font-medium"
                  dominantBaseline="middle"
                  textAnchor="middle"
                  x={label.x}
                  y={label.y}
                >
                  {biomarkerLabels[key]}
                </text>
              </g>
            );
          })}

          <polygon
            className="fill-accent/25 stroke-accent"
            points={polygon}
            strokeLinejoin="round"
            strokeWidth="2"
          />

          {points.map((point, index) => (
            <circle
              className="fill-accent stroke-background"
              cx={point.x}
              cy={point.y}
              key={order[index]}
              r="4"
              strokeWidth="2"
            />
          ))}
        </svg>

        <div className="space-y-3 self-center">
          {order.map((key) => (
            <div key={key}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="font-medium">{biomarkerLabels[key]}</span>
                <span className="font-semibold">{Math.round(biomarkers[key] * 100)}%</span>
              </div>
              <div className="h-2 rounded-full bg-surface-tertiary">
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${Math.round(biomarkers[key] * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function polarPoint(cx, cy, radius, index, total) {
  const angle = -Math.PI / 2 + (2 * Math.PI * index) / total;

  return {
    x: Number((cx + radius * Math.cos(angle)).toFixed(2)),
    y: Number((cy + radius * Math.sin(angle)).toFixed(2)),
  };
}
