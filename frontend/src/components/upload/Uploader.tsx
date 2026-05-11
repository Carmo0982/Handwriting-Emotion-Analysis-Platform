import {
  Button,
  Card,
  Chip,
  Modal,
  ProgressBar,
  Spinner,
  useOverlayState,
} from "@heroui/react";
import { AlertTriangle, CheckCircle2, FileImage, RefreshCcw, UploadCloud } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import {
  type AnalysisResult,
  uploadHandwritingAnalysis,
} from "../../services/api";

type Tenant = {
  id: string;
  name: string;
};

type UploaderProps = {
  tenant: Tenant;
  onAnalysisComplete: (result: AnalysisResult) => void;
  onProcessingChange: (isProcessing: boolean) => void;
  onProgressChange: (progress: number) => void;
};

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const VALID_TYPES = ["image/jpeg", "image/png"];

export default function Uploader({
  tenant,
  onAnalysisComplete,
  onProcessingChange,
  onProgressChange,
}: UploaderProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const progressTimerRef = useRef<number | null>(null);
  const validationTokenRef = useRef(0);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const errorModal = useOverlayState({
    isOpen: Boolean(errorMessage),
    onOpenChange: (isOpen) => {
      if (!isOpen) setErrorMessage("");
    },
  });

  useEffect(() => {
    onProcessingChange(isLoading);
  }, [isLoading, onProcessingChange]);

  useEffect(() => {
    onProgressChange(progress);
  }, [onProgressChange, progress]);

  useEffect(() => {
    if (!file) {
      setPreviewUrl("");
      return undefined;
    }

    const nextPreviewUrl = URL.createObjectURL(file);
    setPreviewUrl(nextPreviewUrl);

    return () => URL.revokeObjectURL(nextPreviewUrl);
  }, [file]);

  useEffect(
    () => () => {
      if (progressTimerRef.current) {
        window.clearInterval(progressTimerRef.current);
      }
    },
    [],
  );

  async function selectFile(nextFile?: File) {
    const validationError = validateFile(nextFile);

    setSuccessMessage("");

    if (validationError) {
      setFile(null);
      setProgress(0);
      setErrorMessage(validationError);
      return;
    }

    const token = ++validationTokenRef.current;
    setProgress(4);

    const contentError = nextFile ? await validateHandwritingImage(nextFile) : "";
    if (validationTokenRef.current !== token) return;

    if (contentError) {
      setFile(null);
      setProgress(0);
      setErrorMessage(contentError);
      return;
    }

    setFile(nextFile ?? null);
    setProgress(8);
  }

  async function submitAnalysis() {
    if (!file) {
      setErrorMessage("Selecciona una imagen JPG o PNG antes de enviar.");
      return;
    }

    setIsLoading(true);
    setSuccessMessage("");
    setProgress(12);
    startSyntheticProgress();

    try {
      const result = await uploadHandwritingAnalysis({
        file,
        tenant,
        onUploadProgress: (event) => {
          if (!event.total) return;
          const uploadProgress = Math.round((event.loaded / event.total) * 42);
          setProgress(Math.max(18, uploadProgress));
        },
      });

      setProgress(100);
      setSuccessMessage("Análisis completado correctamente.");
      onAnalysisComplete(result);
    } catch (error) {
      setProgress(0);
      setErrorMessage(error instanceof Error ? error.message : "No se pudo procesar la imagen.");
    } finally {
      stopSyntheticProgress();
      setIsLoading(false);
    }
  }

  function reset() {
    stopSyntheticProgress();
    setFile(null);
    setPreviewUrl("");
    setProgress(0);
    setErrorMessage("");
    setSuccessMessage("");
  }

  function startSyntheticProgress() {
    stopSyntheticProgress();
    progressTimerRef.current = window.setInterval(() => {
      setProgress((currentProgress) => {
        if (currentProgress >= 88) return currentProgress;
        return currentProgress + 4;
      });
    }, 260);
  }

  function stopSyntheticProgress() {
    if (progressTimerRef.current) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
  }

  return (
    <>
      <Card className="rounded-lg border border-border/70 animate-enter" variant="default">
        <Card.Header>
          <div className="flex w-full flex-wrap items-start justify-between gap-3">
            <div>
              <Card.Title>Carga de muestra</Card.Title>
              <Card.Description>Sube una imagen para analizar el trazo.</Card.Description>
            </div>
            <Chip color={isLoading ? "warning" : successMessage ? "success" : "accent"} variant="soft">
              {isLoading ? "procesando" : successMessage ? "completado" : "en espera"}
            </Chip>
          </div>
        </Card.Header>

        <Card.Content className="space-y-4">
          <button
            className={`analysis-dropzone flex w-full flex-col items-center justify-center rounded-lg border border-dashed p-5 text-center transition ${
              isDragging
                ? "border-accent bg-accent-soft text-accent-soft-foreground"
                : "border-border bg-surface-secondary/65 hover:border-accent"
            }`}
            onClick={() => inputRef.current?.click()}
            onDragEnter={(event) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={(event) => {
              event.preventDefault();
              setIsDragging(false);
            }}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              setIsDragging(false);
              void selectFile(Array.from(event.dataTransfer.files)[0]);
            }}
            type="button"
          >
            <input
              accept="image/png,image/jpeg"
              className="hidden"
              onChange={(event) => void selectFile(Array.from(event.target.files ?? [])[0])}
              ref={inputRef}
              type="file"
            />

            {previewUrl ? (
              <img
                alt="Vista previa de la muestra"
                className="h-52 w-full rounded-lg object-cover shadow-sm"
                src={previewUrl}
              />
            ) : (
              <div className="grid size-20 place-items-center rounded-lg bg-surface text-accent shadow-sm">
                <UploadCloud size={34} />
              </div>
            )}

            <div className="mt-4 max-w-sm">
              <p className="text-lg font-semibold">
                {file ? file.name : "Arrastra una muestra manuscrita"}
              </p>
              <p className="mt-1 text-sm text-muted">JPG o PNG, máximo 10 MB</p>
            </div>
          </button>

          <ProgressBar value={progress}>
            <div className="mb-2 flex items-center justify-between gap-3 text-sm">
              <span className="font-medium">Progreso del análisis</span>
              <ProgressBar.Output className="font-semibold" />
            </div>
            <ProgressBar.Track className="h-2.5 rounded-full bg-surface-tertiary">
              <ProgressBar.Fill className="rounded-full bg-accent transition-all" />
            </ProgressBar.Track>
          </ProgressBar>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {["Carga", "Almacenamiento", "Análisis", "Resultados"].map((step, index) => (
              <div
                className={`rounded-md border px-2 py-2 text-center text-[11px] font-medium leading-tight sm:text-xs ${
                  progress >= [8, 28, 62, 100][index]
                    ? "border-accent/40 bg-accent-soft/80 text-accent-soft-foreground"
                    : "border-border bg-surface-secondary text-muted"
                }`}
                key={step}
              >
                <span className="break-words">{step}</span>
              </div>
            ))}
          </div>

          {successMessage ? (
            <div className="flex items-center gap-2 rounded-md border border-success/35 bg-success/10 px-3 py-2 text-sm text-success">
              <CheckCircle2 size={16} />
              {successMessage}
            </div>
          ) : null}
        </Card.Content>

        <Card.Footer className="flex flex-wrap gap-2">
          <Button
            className="w-full sm:min-w-44 sm:w-auto"
            isDisabled={!file || isLoading}
            isPending={isLoading}
            onPress={submitAnalysis}
            variant="primary"
          >
            {({ isPending }) => (
              <>
                {isPending ? <Spinner color="accent" size="sm" /> : <UploadCloud size={17} />}
                {isPending ? "Procesando" : "Enviar muestra"}
              </>
            )}
          </Button>

          <Button className="w-full sm:w-auto" onPress={() => inputRef.current?.click()} variant="secondary">
            <FileImage size={17} />
            Elegir imagen
          </Button>

          <Button className="w-full sm:w-auto" isDisabled={isLoading && !file} onPress={reset} variant="ghost">
            <RefreshCcw size={16} />
            Limpiar
          </Button>
        </Card.Footer>
      </Card>

      <Modal state={errorModal}>
        <Modal.Backdrop variant="blur">
          <Modal.Container placement="center" size="md">
            <Modal.Dialog>
              <Modal.CloseTrigger />
              <Modal.Header>
                <Modal.Icon className="bg-danger/15 text-danger">
                  <AlertTriangle size={22} />
                </Modal.Icon>
                <Modal.Heading>Error en la carga</Modal.Heading>
              </Modal.Header>
              <Modal.Body>
                <p className="text-sm leading-6 text-muted">{errorMessage}</p>
              </Modal.Body>
              <Modal.Footer>
                <Button onPress={() => setErrorMessage("")} variant="primary">
                  Entendido
                </Button>
              </Modal.Footer>
            </Modal.Dialog>
          </Modal.Container>
        </Modal.Backdrop>
      </Modal>
    </>
  );
}

function validateFile(file?: File): string {
  if (!file) {
    return "Selecciona una imagen de escritura manuscrita.";
  }

  if (!VALID_TYPES.includes(file.type)) {
    return "Formato no compatible. Solo JPG o PNG.";
  }

  if (file.size > MAX_FILE_SIZE) {
    return "La imagen supera el limite de 10 MB.";
  }

  return "";
}

async function validateHandwritingImage(file: File): Promise<string> {
  if (!("createImageBitmap" in window)) {
    return "";
  }

  let bitmap: ImageBitmap | null = null;

  try {
    bitmap = await createImageBitmap(file);
  } catch (error) {
    return "No se pudo leer la imagen. Intenta con otra foto.";
  }

  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;

  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) {
    bitmap.close();
    return "";
  }

  context.drawImage(bitmap, 0, 0, size, size);
  bitmap.close();

  const { data } = context.getImageData(0, 0, size, size);
  const totalPixels = size * size;
  let luminanceSum = 0;
  let luminanceSqSum = 0;
  let darkPixels = 0;
  let lightPixels = 0;
  let saturationSum = 0;

  for (let i = 0; i < data.length; i += 4) {
    const red = data[i] / 255;
    const green = data[i + 1] / 255;
    const blue = data[i + 2] / 255;

    const max = Math.max(red, green, blue);
    const min = Math.min(red, green, blue);
    const saturation = max === 0 ? 0 : (max - min) / max;
    const luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue;

    saturationSum += saturation;
    luminanceSum += luminance;
    luminanceSqSum += luminance * luminance;

    if (luminance < 0.32) darkPixels += 1;
    if (luminance > 0.86) lightPixels += 1;
  }

  const lightRatio = lightPixels / totalPixels;
  const darkRatio = darkPixels / totalPixels;
  const averageSaturation = saturationSum / totalPixels;
  const meanLuminance = luminanceSum / totalPixels;
  const variance = luminanceSqSum / totalPixels - meanLuminance * meanLuminance;

  if (variance < 0.006) {
    return "La imagen no tiene suficiente contraste para detectar escritura.";
  }

  if (darkRatio < 0.006) {
    return "No se detecta escritura. Usa una foto clara de texto manuscrito.";
  }

  if (darkRatio > 0.7 || lightRatio < 0.1) {
    return "La imagen no parece manuscrita. Sube una hoja con texto a mano.";
  }

  if (averageSaturation > 0.4 && lightRatio < 0.6) {
    return "La imagen parece una foto. Sube una hoja con escritura a mano.";
  }

  return "";
}
