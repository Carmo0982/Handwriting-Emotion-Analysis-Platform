import { Button, Card, Chip, Spinner } from "@heroui/react";
import { Brain, FileImage, RefreshCcw, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";

export default function UploadDropzone({ upload }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  function handleFileList(fileList) {
    const [nextFile] = Array.from(fileList ?? []);
    upload.selectFile(nextFile);
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    handleFileList(event.dataTransfer.files);
  }

  return (
    <Card className="rounded-lg border border-border/70" variant="default">
      <Card.Header>
        <div className="flex w-full items-start justify-between gap-3">
          <div>
            <Card.Title>Upload Service Interface</Card.Title>
            <Card.Description>POST /v1/analysis/upload</Card.Description>
          </div>
          <Chip color={upload.isProcessing ? "warning" : "accent"} variant="soft">
            {upload.isProcessing ? "processing" : "sync prototype"}
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
          onDrop={handleDrop}
          type="button"
        >
          <input
            accept="image/png,image/jpeg"
            className="hidden"
            onChange={(event) => handleFileList(event.target.files)}
            ref={inputRef}
            type="file"
          />

          {upload.previewUrl ? (
            <img
              alt="Muestra manuscrita"
              className="h-48 w-full rounded-lg object-cover shadow-sm"
              src={upload.previewUrl}
            />
          ) : (
            <div className="grid size-20 place-items-center rounded-lg bg-surface text-accent shadow-sm">
              <UploadCloud size={34} />
            </div>
          )}

          <div className="mt-4 max-w-sm">
            <p className="text-lg font-semibold">
              {upload.file ? upload.file.name : "Muestra manuscrita"}
            </p>
            <p className="mt-1 text-sm text-muted">JPG o PNG, maximo 10 MB</p>
          </div>
        </button>

        {upload.error ? (
          <div className="rounded-md border border-danger/35 bg-danger/10 px-3 py-2 text-sm text-danger">
            {upload.error}
          </div>
        ) : null}

        <div className="grid grid-cols-4 gap-2">
          {["Carga", "Preproceso", "Inferencia", "JSON"].map((step, index) => (
            <div
              className={`rounded-md border px-2 py-2 text-center text-xs font-medium ${
                upload.isProcessing || upload.result
                  ? "border-accent/40 bg-accent-soft/80 text-accent-soft-foreground"
                  : index === 0 && upload.file
                    ? "border-accent/40 bg-accent-soft/80 text-accent-soft-foreground"
                    : "border-border bg-surface-secondary text-muted"
              }`}
              key={step}
            >
              {step}
            </div>
          ))}
        </div>
      </Card.Content>

      <Card.Footer className="flex flex-wrap gap-2">
        <Button
          className="min-w-44"
          isDisabled={!upload.file || upload.isProcessing}
          isPending={upload.isProcessing}
          onPress={upload.runAnalysis}
          variant="primary"
        >
          {({ isPending }) => (
            <>
              {isPending ? <Spinner color="accent" size="sm" /> : <Brain size={17} />}
              {isPending ? "Procesando" : "Ejecutar analisis"}
            </>
          )}
        </Button>

        <Button onPress={() => inputRef.current?.click()} variant="secondary">
          <FileImage size={17} />
          Seleccionar
        </Button>

        <Button
          isDisabled={upload.isProcessing && !upload.file}
          onPress={upload.reset}
          variant="ghost"
        >
          <RefreshCcw size={16} />
          Limpiar
        </Button>
      </Card.Footer>
    </Card>
  );
}
