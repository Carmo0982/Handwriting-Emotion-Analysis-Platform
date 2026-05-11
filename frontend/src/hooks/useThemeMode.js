import { useEffect, useState } from "react";

const STORAGE_KEY = "tdse-theme-mode";

export function useThemeMode() {
  const [mode, setMode] = useState(() => {
    const storedMode = window.localStorage.getItem(STORAGE_KEY);

    if (storedMode === "dark" || storedMode === "light") {
      return storedMode;
    }

    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    const root = document.documentElement;

    root.classList.toggle("dark", mode === "dark");
    root.classList.toggle("light", mode === "light");
    root.dataset.theme = mode;
    window.localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);

  function toggleMode() {
    setMode((currentMode) => (currentMode === "dark" ? "light" : "dark"));
  }

  return { mode, toggleMode };
}
