import { Card, Chip } from "@heroui/react";
import { BrainCircuit, Clock3, Layers3, ShieldCheck } from "lucide-react";

import InferenceResults from "../analysis/InferenceResults.jsx";
import ScreeningHistory from "../history/ScreeningHistory.jsx";
import UploadDropzone from "../upload/UploadDropzone.jsx";
import { useAnalysisUpload } from "../../hooks/useAnalysisUpload.js";

export default function Dashboard({ tenant, history, onAnalysisComplete }) {
  const upload = useAnalysisUpload(tenant, onAnalysisComplete);
  const highPriority = history.filter((item) => item.prediction.confidence >= 0.75).length;
  const averageLatency =
    history.length === 0
      ? 0
      : Math.round(
          history.reduce((total, item) => total + item.latencyMs, 0) / history.length,
        );

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-5">
      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={BrainCircuit}
          label="Modelo"
          tone="accent"
          value="CNN + ViT"
          detail="inferencia hibrida"
        />
        <StatCard
          icon={Clock3}
          label="Latencia media"
          tone="success"
          value={averageLatency ? `${averageLatency} ms` : "sin datos"}
          detail="objetivo < 2s"
        />
        <StatCard
          icon={Layers3}
          label="Analisis del tenant"
          tone="warning"
          value={history.length}
          detail={`${tenant.analysesToday} eventos hoy`}
        />
        <StatCard
          icon={ShieldCheck}
          label="Cola preventiva"
          tone="danger"
          value={highPriority + tenant.riskQueue}
          detail="requieren revision"
        />
      </section>

      <section className="grid items-start gap-5 xl:grid-cols-[minmax(360px,0.92fr)_minmax(0,1.35fr)]">
        <UploadDropzone upload={upload} />
        <InferenceResults isProcessing={upload.isProcessing} result={upload.result} />
      </section>

      <ScreeningHistory history={history} />
    </div>
  );
}

function StatCard({ detail, icon: Icon, label, tone, value }) {
  const colorByTone = {
    accent: "accent",
    success: "success",
    warning: "warning",
    danger: "danger",
  };

  return (
    <Card className="rounded-lg border border-border/70" variant="default">
      <Card.Content className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted">
            {label}
          </p>
          <p className="mt-1 truncate text-2xl font-semibold">{value}</p>
          <p className="mt-1 text-sm text-muted">{detail}</p>
        </div>
        <Chip color={colorByTone[tone]} size="lg" variant="soft">
          <Icon size={20} />
        </Chip>
      </Card.Content>
    </Card>
  );
}
