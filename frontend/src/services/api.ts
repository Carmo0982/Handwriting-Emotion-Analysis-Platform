import axios, { AxiosError, type AxiosRequestConfig } from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8002";
const ANALYSIS_UPLOAD_PATH =
  import.meta.env.VITE_ANALYSIS_UPLOAD_PATH ?? "/v1/analysis/upload";
const DEMO_FALLBACK_ENABLED = import.meta.env.VITE_DEMO_FALLBACK !== "false";
const ACCESS_TOKEN_KEY = "handwriting_access_token";
const TENANT_ID_KEY = "handwriting_tenant_id";

type Tenant = {
  id: string;
  name: string;
};

type UploadArgs = {
  file: File;
  tenant: Tenant;
  onUploadProgress?: AxiosRequestConfig["onUploadProgress"];
};

export type EmotionLabel = "ansiedad" | "estres" | "depresion" | "neutro";

export type AnalysisResult = {
  id: string;
  endpoint: string;
  tenantId: string;
  tenantName: string;
  patientRef: string;
  createdAt: string;
  image: {
    name: string;
    type: string;
    size: number;
  };
  prediction: {
    label: EmotionLabel;
    confidence: number;
  };
  probabilities: Record<EmotionLabel, number>;
  biomarkers: {
    pressure: number;
    rhythm: number;
    slant: number;
    spacing: number;
    strokeVariability: number;
  };
  latencyMs: number;
  model: {
    architecture: string;
    version: string;
  };
  recommendation: string;
  raw: unknown;
};

type ApiContext = {
  accessToken?: string;
  tenantId?: string;
};

const apiContext: ApiContext = {};

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

apiClient.interceptors.request.use((config) => {
  const accessToken =
    apiContext.accessToken ??
    window.localStorage.getItem(ACCESS_TOKEN_KEY) ??
    import.meta.env.VITE_DEMO_JWT;
  const tenantId =
    apiContext.tenantId ?? window.localStorage.getItem(TENANT_ID_KEY);

  config.headers = config.headers ?? {};

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

  if (tenantId) {
    config.headers["x-tenant-id"] = tenantId;
    config.headers["X-Tenant-Id"] = tenantId;
  }

  return config;
});

export function setApiContext({ accessToken, tenantId }: ApiContext) {
  apiContext.accessToken = accessToken;
  apiContext.tenantId = tenantId;

  if (accessToken) {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  }

  if (tenantId) {
    window.localStorage.setItem(TENANT_ID_KEY, tenantId);
  }
}

export async function uploadHandwritingAnalysis({
  file,
  tenant,
  onUploadProgress,
}: UploadArgs): Promise<AnalysisResult> {
  setApiContext({ tenantId: tenant.id });

  const formData = new FormData();
  formData.append("file", file);
  formData.append("tenant_id", tenant.id);

  const startedAt = performance.now();

  try {
    const response = await apiClient.post(ANALYSIS_UPLOAD_PATH, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress,
    });

    return normalizeAnalysisResponse(response.data, {
      file,
      tenant,
      latencyMs: Math.round(performance.now() - startedAt),
    });
  } catch (error) {
    if (DEMO_FALLBACK_ENABLED) {
      await wait(650);
      return createDemoAnalysis(file, tenant, Math.round(performance.now() - startedAt));
    }

    throw new Error(formatApiError(error));
  }
}

function normalizeAnalysisResponse(
  payload: any,
  context: { file: File; tenant: Tenant; latencyMs: number },
): AnalysisResult {
  const inference = payload?.result ?? payload?.analysis ?? payload?.inference ?? payload;
  const predictionLabel = normalizeEmotionLabel(
    inference?.prediction?.label ??
      inference?.prediction ??
      inference?.emotion ??
      inference?.label ??
      "neutro",
  );
  const rawConfidence =
    inference?.prediction?.confidence ?? inference?.confidence ?? inference?.score ?? 0.72;
  const probabilities = normalizeProbabilities(
    inference?.probabilities ?? inference?.scores ?? inference?.emotions,
    predictionLabel,
    rawConfidence,
  );
  const biomarkers = normalizeBiomarkers(inference?.biomarkers ?? inference?.metrics);

  return {
    id: String(payload?.id ?? payload?.analysis_id ?? payload?.image_id ?? crypto.randomUUID()),
    endpoint: `POST ${ANALYSIS_UPLOAD_PATH}`,
    tenantId: String(payload?.tenant_id ?? context.tenant.id),
    tenantName: context.tenant.name,
    patientRef: String(payload?.patient_ref ?? payload?.user_id ?? "demo-session"),
    createdAt: String(payload?.created_at ?? new Date().toISOString()),
    image: {
      name: context.file.name,
      type: context.file.type,
      size: context.file.size,
    },
    prediction: {
      label: predictionLabel,
      confidence: normalizeRatio(rawConfidence),
    },
    probabilities,
    biomarkers,
    latencyMs: Number(payload?.latency_ms ?? context.latencyMs),
    model: {
      architecture:
        String(payload?.model?.architecture ?? inference?.model ?? "CNN + ViT"),
      version: String(payload?.model?.version ?? "aws-gateway"),
    },
    recommendation: buildRecommendation(predictionLabel),
    raw: payload,
  };
}

function createDemoAnalysis(file: File, tenant: Tenant, latencyMs: number): AnalysisResult {
  const seed =
    Array.from(file.name).reduce((total, char) => total + char.charCodeAt(0), 0) +
    file.size;
  const probabilities = normalizeProbabilities(
    {
      ansiedad: 0.31 + ((seed % 43) / 100),
      estres: 0.26 + (((seed >> 2) % 41) / 100),
      depresion: 0.18 + (((seed >> 4) % 38) / 100),
      neutro: 0.15 + (((seed >> 6) % 34) / 100),
    },
    "neutro",
    0.64,
  );
  const [label, confidence] = Object.entries(probabilities).sort((a, b) => b[1] - a[1])[0] as [
    EmotionLabel,
    number,
  ];

  return {
    id: `demo-${crypto.randomUUID().slice(0, 8)}`,
    endpoint: `POST ${ANALYSIS_UPLOAD_PATH}`,
    tenantId: tenant.id,
    tenantName: tenant.name,
    patientRef: `PAC-${Math.floor(1000 + Math.random() * 9000)}`,
    createdAt: new Date().toISOString(),
    image: {
      name: file.name,
      type: file.type,
      size: file.size,
    },
    prediction: {
      label,
      confidence,
    },
    probabilities,
    biomarkers: {
      pressure: clamp(probabilities.ansiedad * 0.64 + probabilities.estres * 0.3, 0.12, 0.95),
      rhythm: clamp(probabilities.estres * 0.76 + 0.13, 0.1, 0.95),
      slant: clamp(probabilities.ansiedad * 0.42 + probabilities.depresion * 0.35, 0.08, 0.9),
      spacing: clamp(probabilities.depresion * 0.68 + probabilities.neutro * 0.16, 0.1, 0.88),
      strokeVariability: clamp(probabilities.ansiedad * 0.38 + probabilities.estres * 0.45, 0.12, 0.92),
    },
    latencyMs,
    model: {
      architecture: "CNN + ViT",
      version: "demo-fallback",
    },
    recommendation: buildRecommendation(label),
    raw: {
      source: "demo-fallback",
      reason: "API Gateway unavailable or demo fallback enabled",
    },
  };
}

function normalizeProbabilities(
  source: any,
  predictionLabel: EmotionLabel,
  confidence: unknown,
): Record<EmotionLabel, number> {
  const base = {
    ansiedad: normalizeRatio(source?.ansiedad ?? source?.anxiety ?? 0.2),
    estres: normalizeRatio(source?.estres ?? source?.stress ?? 0.2),
    depresion: normalizeRatio(source?.depresion ?? source?.depression ?? 0.2),
    neutro: normalizeRatio(source?.neutro ?? source?.neutral ?? 0.2),
  };

  base[predictionLabel] = Math.max(base[predictionLabel], normalizeRatio(confidence));

  return base;
}

function normalizeBiomarkers(source: any): AnalysisResult["biomarkers"] {
  return {
    pressure: normalizeRatio(source?.pressure ?? source?.presion ?? 0.54),
    rhythm: normalizeRatio(source?.rhythm ?? source?.ritmo ?? 0.51),
    slant: normalizeRatio(source?.slant ?? source?.inclinacion ?? 0.48),
    spacing: normalizeRatio(source?.spacing ?? source?.espaciado ?? 0.46),
    strokeVariability: normalizeRatio(
      source?.strokeVariability ?? source?.stroke_variability ?? source?.variabilidad ?? 0.5,
    ),
  };
}

function normalizeEmotionLabel(label: unknown): EmotionLabel {
  const normalized = String(label)
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

  if (["anxiety", "ansiedad"].includes(normalized)) return "ansiedad";
  if (["stress", "estres"].includes(normalized)) return "estres";
  if (["depression", "depresion"].includes(normalized)) return "depresion";

  return "neutro";
}

function normalizeRatio(value: unknown): number {
  const numberValue = Number(value);

  if (Number.isNaN(numberValue)) {
    return 0;
  }

  return clamp(numberValue > 1 ? numberValue / 100 : numberValue, 0, 1);
}

function clamp(value: number, min: number, max: number): number {
  return Number(Math.min(max, Math.max(min, value)).toFixed(2));
}

function buildRecommendation(label: EmotionLabel): string {
  const copy = {
    ansiedad: "Sugerir seguimiento y confirmar con entrevista cl\u00ednica.",
    estres: "Revisar carga reciente y activar apoyo si el patr\u00f3n persiste.",
    depresion: "Derivar a evaluaci\u00f3n profesional y validar con instrumentos cl\u00ednicos.",
    neutro: "Mantener monitoreo peri\u00f3dico sin alertas.",
  };

  return copy[label];
}

function formatApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<any>;
    const detail =
      axiosError.response?.data?.detail ??
      axiosError.response?.data?.message ??
      axiosError.message;

    return `El servicio respondi\u00f3 con error: ${detail}`;
  }

  return error instanceof Error ? error.message : "No se pudo completar el an\u00e1lisis.";
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
