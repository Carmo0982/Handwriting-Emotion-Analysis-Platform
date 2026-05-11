const SUPPORTED_TYPES = ["image/jpeg", "image/png"];
const MAX_FILE_SIZE = 10 * 1024 * 1024;

const emotionKeys = ["ansiedad", "estres", "depresion", "neutro"];

export function validateImageFile(file) {
  if (!file) {
    return "Selecciona una muestra manuscrita.";
  }

  if (!SUPPORTED_TYPES.includes(file.type)) {
    return "Formato no admitido. Usa JPG o PNG.";
  }

  if (file.size > MAX_FILE_SIZE) {
    return "La imagen supera el limite de 10 MB.";
  }

  return "";
}

export async function postAnalysisUpload({ file, tenant }) {
  const validationError = validateImageFile(file);

  if (validationError) {
    throw new Error(validationError);
  }

  const startedAt = performance.now();
  await wait(1300 + Math.round(Math.random() * 650));

  const inference = buildInference(file);
  const latencyMs = Math.round(performance.now() - startedAt);
  const now = new Date();

  return {
    id: `scr-${Math.floor(1000 + Math.random() * 9000)}`,
    endpoint: "POST /v1/analysis/upload",
    tenantId: tenant.id,
    tenantName: tenant.name,
    patientRef: `PAC-${String(Math.floor(1000 + Math.random() * 9000))}`,
    createdAt: now.toISOString(),
    image: {
      name: file.name,
      type: file.type,
      size: file.size,
    },
    pipeline: [
      { name: "Upload Service", status: "completed", detail: "S3 tenant path" },
      { name: "Preprocessing", status: "completed", detail: "224x224 grayscale" },
      { name: "AI Inference", status: "completed", detail: "CNN + ViT" },
      { name: "Results Service", status: "completed", detail: "tenant-aware JSON" },
    ],
    prediction: inference.prediction,
    probabilities: inference.probabilities,
    biomarkers: inference.biomarkers,
    latencyMs,
    model: {
      architecture: "Hybrid CNN + Vision Transformer",
      version: "prototype-sync-0.3",
    },
    recommendation: buildRecommendation(inference.prediction.label),
  };
}

function buildInference(file) {
  const seed =
    Array.from(file.name).reduce((total, char) => total + char.charCodeAt(0), 0) +
    file.size;

  const probabilities = {
    ansiedad: clamp(0.24 + ((seed % 41) / 100), 0.12, 0.92),
    estres: clamp(0.28 + (((seed >> 2) % 38) / 100), 0.1, 0.9),
    depresion: clamp(0.18 + (((seed >> 4) % 36) / 100), 0.08, 0.86),
    neutro: clamp(0.16 + (((seed >> 6) % 35) / 100), 0.08, 0.78),
  };

  const [label, confidence] = emotionKeys
    .map((key) => [key, probabilities[key]])
    .sort((a, b) => b[1] - a[1])[0];

  return {
    prediction: { label, confidence },
    probabilities,
    biomarkers: {
      pressure: clamp(probabilities.ansiedad * 0.72 + probabilities.estres * 0.22, 0.12, 0.94),
      rhythm: clamp(probabilities.estres * 0.78 + 0.11, 0.1, 0.95),
      slant: clamp(probabilities.ansiedad * 0.43 + probabilities.depresion * 0.36, 0.08, 0.9),
      spacing: clamp(probabilities.depresion * 0.7 + probabilities.neutro * 0.12, 0.1, 0.88),
      strokeVariability: clamp(probabilities.ansiedad * 0.38 + probabilities.estres * 0.48, 0.12, 0.92),
    },
  };
}

function buildRecommendation(label) {
  const copy = {
    ansiedad: "Priorizar seguimiento preventivo y correlacionar con entrevista clinica.",
    estres: "Revisar carga reciente y activar ruta de bienestar si el patron persiste.",
    depresion: "Escalar a revision profesional y contrastar con instrumentos psicometricos.",
    neutro: "Mantener monitoreo periodico sin alerta prioritaria.",
  };

  return copy[label] ?? copy.neutro;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, Number(value.toFixed(2))));
}

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
