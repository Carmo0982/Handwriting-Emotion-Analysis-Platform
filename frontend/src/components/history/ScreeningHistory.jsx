import { Card, Chip, ProgressBar } from "@heroui/react";
import { CalendarClock } from "lucide-react";

import { emotionMeta } from "../../data/mockData.js";

export default function ScreeningHistory({ history }) {
  return (
    <Card className="rounded-lg border border-border/70" variant="default">
      <Card.Header>
        <div className="flex w-full flex-wrap items-start justify-between gap-3">
          <div>
            <Card.Title>Dashboard de Analisis</Card.Title>
            <Card.Description>Ultimos diagnosticos preventivos por tenant</Card.Description>
          </div>
          <Chip color="accent" variant="soft">
            {history.length} registros
          </Chip>
        </div>
      </Card.Header>

      <Card.Content>
        <div className="scrollbar-soft overflow-x-auto">
          <div className="min-w-[820px] space-y-2">
            <div className="grid grid-cols-[1.1fr_1fr_1fr_1fr_1.2fr] gap-3 px-3 text-xs font-semibold uppercase tracking-[0.18em] text-muted">
              <span>Paciente</span>
              <span>Fecha</span>
              <span>Prediccion</span>
              <span>Confianza</span>
              <span>Biomarcador dominante</span>
            </div>

            {history.map((item) => (
              <HistoryRow item={item} key={item.id} />
            ))}
          </div>
        </div>
      </Card.Content>
    </Card>
  );
}

function HistoryRow({ item }) {
  const meta = emotionMeta[item.prediction.label] ?? emotionMeta.neutro;
  const confidence = Math.round(item.prediction.confidence * 100);
  const topBiomarker = Object.entries(item.biomarkers).sort((a, b) => b[1] - a[1])[0];

  return (
    <article className="grid grid-cols-[1.1fr_1fr_1fr_1fr_1.2fr] items-center gap-3 rounded-lg border border-border/70 bg-surface-secondary/64 px-3 py-3">
      <div>
        <p className="font-semibold">{item.patientRef}</p>
        <p className="text-xs text-muted">{item.id}</p>
      </div>

      <div className="flex items-center gap-2 text-sm">
        <CalendarClock size={15} />
        {formatDate(item.createdAt)}
      </div>

      <Chip color={meta.color} variant="soft">
        {meta.label}
      </Chip>

      <ProgressBar value={confidence}>
        <ProgressBar.Track className="h-2 rounded-full bg-surface-tertiary">
          <ProgressBar.Fill className="rounded-full bg-accent" />
        </ProgressBar.Track>
      </ProgressBar>

      <div>
        <p className="text-sm font-medium">{biomarkerName(topBiomarker[0])}</p>
        <p className="text-xs text-muted">{Math.round(topBiomarker[1] * 100)}%</p>
      </div>
    </article>
  );
}

function formatDate(value) {
  return new Intl.DateTimeFormat("es-CO", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
  }).format(new Date(value));
}

function biomarkerName(key) {
  const names = {
    pressure: "Presion",
    rhythm: "Ritmo",
    slant: "Inclinacion",
    spacing: "Espaciado",
    strokeVariability: "Variabilidad",
  };

  return names[key] ?? key;
}
