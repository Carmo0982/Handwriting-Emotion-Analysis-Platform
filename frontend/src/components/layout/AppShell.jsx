import { Button, Tooltip } from "@heroui/react";
import { Bell, Moon, Sun } from "lucide-react";

import TenantSidebar from "./TenantSidebar.jsx";

export default function AppShell({
  children,
  mode,
  tenant,
  tenants,
  onTenantChange,
  onToggleMode,
}) {
  const ThemeIcon = mode === "dark" ? Sun : Moon;

  return (
    <div className="app-bg min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <TenantSidebar
          tenant={tenant}
          tenants={tenants}
          onTenantChange={onTenantChange}
        />

        <main className="min-w-0 flex-1">
          <header className="sticky top-0 z-20 border-b border-border/70 bg-background/86 px-4 py-3 backdrop-blur-xl md:px-8">
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted">
                  TDSE Emotion Cloud
                </p>
                <h1 className="truncate text-xl font-semibold md:text-2xl">
                  Screening preventivo manuscrito
                </h1>
              </div>

              <div className="flex items-center gap-2">
                <Tooltip>
                  <Tooltip.Trigger>
                    <Button
                      aria-label="Notificaciones"
                      className="shrink-0"
                      isIconOnly
                      variant="secondary"
                    >
                      <Bell size={18} />
                    </Button>
                  </Tooltip.Trigger>
                  <Tooltip.Content showArrow>
                    <Tooltip.Arrow />
                    Eventos clinicos
                  </Tooltip.Content>
                </Tooltip>

                <Tooltip>
                  <Tooltip.Trigger>
                    <Button
                      aria-label="Cambiar tema"
                      className="shrink-0"
                      isIconOnly
                      onPress={onToggleMode}
                      variant="secondary"
                    >
                      <ThemeIcon size={18} />
                    </Button>
                  </Tooltip.Trigger>
                  <Tooltip.Content showArrow>
                    <Tooltip.Arrow />
                    Tema {mode === "dark" ? "claro" : "oscuro"}
                  </Tooltip.Content>
                </Tooltip>
              </div>
            </div>
          </header>

          <div className="px-4 py-5 md:px-8 md:py-7">{children}</div>
        </main>
      </div>
    </div>
  );
}
