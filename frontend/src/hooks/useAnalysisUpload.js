import { useEffect, useState } from "react";

import { postAnalysisUpload, validateImageFile } from "../services/analysisService.js";

export function useAnalysisUpload(tenant, onComplete) {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("idle");

  useEffect(() => {
    if (!file) {
      setPreviewUrl("");
      return undefined;
    }

    const nextPreviewUrl = URL.createObjectURL(file);
    setPreviewUrl(nextPreviewUrl);

    return () => URL.revokeObjectURL(nextPreviewUrl);
  }, [file]);

  function selectFile(nextFile) {
    const validationError = validateImageFile(nextFile);

    setResult(null);

    if (validationError) {
      setFile(null);
      setError(validationError);
      setStatus("error");
      return false;
    }

    setFile(nextFile);
    setError("");
    setStatus("ready");
    return true;
  }

  async function runAnalysis() {
    const validationError = validateImageFile(file);

    if (validationError) {
      setError(validationError);
      setStatus("error");
      return null;
    }

    setStatus("processing");
    setError("");

    try {
      const response = await postAnalysisUpload({ file, tenant });
      setResult(response);
      setStatus("complete");
      onComplete?.(response);
      return response;
    } catch (nextError) {
      setError(nextError.message ?? "No se pudo procesar la muestra.");
      setStatus("error");
      return null;
    }
  }

  function reset() {
    setFile(null);
    setPreviewUrl("");
    setResult(null);
    setError("");
    setStatus("idle");
  }

  return {
    error,
    file,
    isProcessing: status === "processing",
    previewUrl,
    result,
    runAnalysis,
    selectFile,
    reset,
    status,
  };
}
