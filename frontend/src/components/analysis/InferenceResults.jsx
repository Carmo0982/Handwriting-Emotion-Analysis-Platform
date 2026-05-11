import { Card, Chip, Label, ProgressBar, Skeleton } from "@heroui/react";
import { Activity, BadgeCheck, Cpu, TimerReset } from "lucide-react";

import { emotionMeta } from "../../data/mockData.js";
import BiomarkerRadar from "./BiomarkerRadar.jsx";
import EmotionBars from "./EmotionBars.jsx";

export default function InferenceResults({ isProcessing, result }) {
  if (isProcessing) {
    return <ProcessingState />;
  }

  if (!result) {
    return (
      <Card className="rounded-lg border border-border/70" variant="default">
        <Card.Header>
          <Card.Title>AI Inference View</Card.Title>
          <Card.Description>Resultado visual del JSON de inferencia</Card.Description>
        </Card.Header>
        <Card.Content className="grid min-h-[460px] place-items-center">
          <div className="max-w-md text-center">
            <div className="mx-auto grid size-20 place-items-center rounded-lg bg-accent-soft text-accent-soft-foreground">
              <Cpu size={34} />
            </div>
            <h2 className="mt-5 text-2xl font-semibold">Sin muestra activa</h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              El resultado aparece cuando el prototipo completa carga, preprocesamiento e
              inferencia.
            </p>
          </div>
        </Card.Content>
      </Card>
    );
  }

  const meta = emotionMeta[result.prediction.label] ?? emotionMeta.neutro;
  const confidence = Math.round(result.prediction.confidence * 100);

  return (
    <Card className="rounded-lg border border-border/70" variant="default">
      <Card.Header>
        <div className="flex w-full flex-wrap items-start justify-between gap-3">
          <div>
            <Card.Title>AI Inference View</Card.Title>
            <Card.Description>{result.model.architecture}</Card.Description>
          </div>
          <Chip color={meta.color} size="lg" variant="primary">
            {meta.label}
          </Chip>
        </div>
      </Card.Header>

      <Card.Content className="space-y-5">
        <div className="grid gap-3 md:grid-cols-3">
          <InferencePill
            icon={BadgeCheck}
            label="Prediccion"
            value={meta.label}
          />
          <InferencePill
            icon={TimerReset}
            label="Latencia"
            value={`${result.latencyMs} ms`}
          />
          <InferencePill
            icon={Activity}
            label="Version"
            value={result.model.version}
          />
        </div>

        <div className="rounded-lg border border-border/70 bg-surface-secondary/60 p-4">
          <ProgressBar value={confidence}>
            <div className="mb-2 flex items-center justify-between gap-3">
              <Label className="text-sm font-medium">Confianza del modelo</Label>
              <ProgressBar.Output className="text-sm font-semibold" />
            </div>
            <ProgressBar.Track className="h-2.5 rounded-full bg-surface-tertiary">
              <ProgressBar.Fill className="rounded-full bg-accent" />
            </ProgressBar.Track>
          </ProgressBar>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1fr_0.9fr]">
          <EmotionBars probabilities={result.probabilities} />
          <BiomarkerRadar biomarkers={result.biomarkers} />
        </div>

        <div className="rounded-lg border border-border/70 bg-surface-secondary/60 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
            Screening preventivo
          </p>
          <p className="mt-2 text-sm leading-6">{result.recommendation}</p>
        </div>
      </Card.Content>
    </Card>
  );
}

function ProcessingState() {
  return (
    <Card className="rounded-lg border border-border/70" variant="default">
      <Card.Header>
        <Card.Title>AI Inference View</Card.Title>
        <Card.Description>Preprocesamiento e inferencia en curso</Card.Description>
      </Card.Header>
      <Card.Content className="skeleton--shimmer space-y-5">
        <div className="grid gap-3 md:grid-cols-3">
          <Skeleton animationType="none" className="h-24 rounded-lg" />
          <Skeleton animationType="none" className="h-24 rounded-lg" />
          <Skeleton animationType="none" className="h-24 rounded-lg" />
        </div>
        <Skeleton animationType="none" className="h-20 rounded-lg" />
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton animationType="none" className="h-72 rounded-lg" />
          <Skeleton animationType="none" className="h-72 rounded-lg" />
        </div>
      </Card.Content>
    </Card>
  );
}

function InferencePill({ icon: Icon, label, value }) {
  return (
    <div className="rounded-lg border border-border/70 bg-surface-secondary/70 p-4">
      <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted">
        <Icon size={15} />
        {label}
      </div>
      <p className="truncate text-lg font-semibold">{value}</p>
    </div>
  );
}
