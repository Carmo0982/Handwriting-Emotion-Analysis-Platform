import { Card, Chip, ProgressCircle, Separator as Divider, Skeleton } from "@heroui/react";
import { BrainCircuit, FileSearch, ShieldCheck } from "lucide-react";

import type { AnalysisResult, EmotionLabel } from "../../services/api";
import { biomarkerLabels, emotionMeta } from "../../data/mockData.js";

type ResultsViewProps = {
  result: AnalysisResult | null;
  isLoading: boolean;
  progress: number;
};

const emotionOrder: EmotionLabel[] = ["ansiedad", "estres", "depresion", "neutro"];

export default function ResultsView({ result, isLoading, progress }: ResultsViewProps) {
  if (isLoading) {
    return <LoadingResults progress={progress} />;
  }

  if (!result) {
    return (
      <Card className="rounded-lg border border-border/70 animate-enter" variant="default">
        <Card.Content className="grid min-h-[420px] place-items-center sm:min-h-[520px]">
          <div className="max-w-md text-center">
            <div className="mx-auto grid size-20 place-items-center rounded-lg bg-accent-soft text-accent-soft-foreground">
              <FileSearch size={34} />
            </div>
            <h2 className="mt-5 text-2xl font-semibold">A&uacute;n no hay an&aacute;lisis</h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              Sube una imagen manuscrita para ver la predicción, la confianza y los
              biomarcadores del trazo.
            </p>
          </div>
        </Card.Content>
      </Card>
    );
  }

  const meta = emotionMeta[result.prediction.label] ?? emotionMeta.neutro;
  const confidence = Math.round(result.prediction.confidence * 100);

  return (
    <Card className="rounded-lg border border-border/70 animate-enter" variant="default">
      <Card.Header>
        <div className="flex w-full flex-wrap items-start justify-between gap-4">
          <div>
            <Card.Title>Resultados del análisis</Card.Title>
            <Card.Description>Modelo {result.model.architecture}</Card.Description>
          </div>
          <Chip color={meta.color} size="lg" variant="primary">
            {meta.label}
          </Chip>
        </div>
      </Card.Header>

      <Card.Content className="space-y-5">
        <section className="grid gap-4 lg:grid-cols-[220px_1fr]">
          <div className="rounded-lg border border-border/70 bg-surface-secondary/60 p-4">
            <p className="mb-4 text-sm font-semibold">Confianza global</p>
            <ConfidenceCircle value={confidence} />
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <ResultMetric icon={BrainCircuit} label="Predicción" value={meta.label} />
            <ResultMetric icon={ShieldCheck} label="Organización" value={result.tenantName} />
          </div>
        </section>

        <Divider className="bg-border" />

        <section className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="rounded-lg border border-border/70 bg-surface-secondary/60 p-4">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold">Distribución emocional</p>
                <p className="text-xs text-muted">Resumen visual del an&aacute;lisis</p>
              </div>
            </div>

            <div className="space-y-4">
              {emotionOrder.map((key) => {
                const percentage = Math.round((result.probabilities[key] ?? 0) * 100);
                const emotion = emotionMeta[key] ?? emotionMeta.neutro;

                return (
                  <div key={key}>
                    <div className="mb-1.5 flex items-center justify-between gap-3 text-sm">
                      <span className="font-medium">{emotion.label}</span>
                      <span className="font-semibold">{percentage}%</span>
                    </div>
                    <div className="h-3 overflow-hidden rounded-full bg-surface-tertiary">
                      <div
                        className={`metric-bar h-full rounded-full ${emotion.riskClass}`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-lg border border-border/70 bg-surface-secondary/60 p-4">
            <p className="text-sm font-semibold">Biomarcadores</p>
            <p className="mb-4 text-xs text-muted">
              presi&oacute;n, inclinaci&oacute;n, ritmo y variabilidad del trazo
            </p>

            <BiomarkerRow label={biomarkerLabels.pressure} value={result.biomarkers.pressure} />
            <Divider className="my-3 bg-border" />
            <BiomarkerRow label={biomarkerLabels.slant} value={result.biomarkers.slant} />
            <Divider className="my-3 bg-border" />
            <BiomarkerRow label={biomarkerLabels.rhythm} value={result.biomarkers.rhythm} />
            <Divider className="my-3 bg-border" />
            <BiomarkerRow
              label={biomarkerLabels.strokeVariability}
              value={result.biomarkers.strokeVariability}
            />
          </div>
        </section>

        <div className="rounded-lg border border-border/70 bg-surface-secondary/60 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
            Recomendaci&oacute;n
          </p>
          <p className="mt-2 text-sm leading-6">{result.recommendation}</p>
        </div>
      </Card.Content>
    </Card>
  );
}

function LoadingResults({ progress }: { progress: number }) {
  return (
    <Card className="rounded-lg border border-border/70 animate-enter" variant="default">
      <Card.Header>
        <Card.Title>Resultados del an&aacute;lisis</Card.Title>
        <Card.Description>Analizando muestra manuscrita</Card.Description>
      </Card.Header>
      <Card.Content className="space-y-5">
        <div className="grid gap-4 lg:grid-cols-[220px_1fr]">
          <div className="rounded-lg border border-border/70 bg-surface-secondary/60 p-4">
            <p className="mb-4 text-sm font-semibold">Progreso</p>
            <ConfidenceCircle value={progress} />
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <Skeleton animationType="pulse" className="h-28 rounded-lg" />
            <Skeleton animationType="pulse" className="h-28 rounded-lg" />
            <Skeleton animationType="pulse" className="h-28 rounded-lg" />
          </div>
        </div>
        <Skeleton animationType="pulse" className="h-72 rounded-lg" />
      </Card.Content>
    </Card>
  );
}

function ConfidenceCircle({ value }: { value: number }) {
  return (
    <ProgressCircle aria-label="Porcentaje de confianza" className="relative mx-auto size-36" value={value}>
      <ProgressCircle.Track className="size-36">
        <ProgressCircle.TrackCircle />
        <ProgressCircle.FillCircle className="stroke-accent" />
      </ProgressCircle.Track>
      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center">
          <p className="text-3xl font-semibold">{value}%</p>
          <p className="text-xs text-muted">confianza</p>
        </div>
      </div>
    </ProgressCircle>
  );
}

function ResultMetric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof BrainCircuit;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border/70 bg-surface-secondary/60 p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted sm:text-xs sm:tracking-[0.18em]">
        <Icon size={15} />
        <span className="min-w-0 break-words">{label}</span>
      </div>
      <p className="break-words text-base font-semibold sm:text-lg">{value}</p>
    </div>
  );
}

function BiomarkerRow({ label, value }: { label: string; value: number }) {
  const percentage = Math.round(value * 100);

  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="font-semibold">{percentage}%</span>
      </div>
      <div className="h-2.5 rounded-full bg-surface-tertiary">
        <div className="h-full rounded-full bg-accent" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}
