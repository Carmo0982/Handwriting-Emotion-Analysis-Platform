import { Card, Chip } from "@heroui/react";
import { BrainCircuit, Layers3, ShieldCheck } from "lucide-react";
import { useState } from "react";

import ResultsView from "../analysis/ResultsView";
import ScreeningHistory from "../history/ScreeningHistory.jsx";
import Uploader from "../upload/Uploader";

export default function Dashboard({ tenant, history, onAnalysisComplete }) {
  const [activeResult, setActiveResult] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const highPriority = history.filter((item) => item.prediction.confidence >= 0.75).length;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-5">
      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <StatCard
          icon={BrainCircuit}
          label="Modelo"
          tone="accent"
          value="CNN + ViT"
          detail="modelo híbrido"
        />
        <StatCard
          icon={Layers3}
          label="Análisis registrados"
          tone="warning"
          value={history.length}
          detail="sesión actual"
        />
        <StatCard
          icon={ShieldCheck}
          label="Casos prioritarios"
          tone="danger"
          value={highPriority}
          detail="según confianza"
        />
      </section>

      <section
        className="grid items-start gap-5 xl:grid-cols-[minmax(360px,0.92fr)_minmax(0,1.35fr)]"
        id="analysis-section"
      >
        <Uploader
          tenant={tenant}
          onAnalysisComplete={(result) => {
            setActiveResult(result);
            onAnalysisComplete(result);
          }}
          onProcessingChange={setIsProcessing}
          onProgressChange={setProgress}
        />
        <ResultsView
          isLoading={isProcessing}
          progress={progress}
          result={activeResult}
        />
      </section>

      <section id="results-section">
        <ScreeningHistory history={history} />
      </section>
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
