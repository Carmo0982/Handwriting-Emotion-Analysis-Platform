import { Button, Card, Chip, Label, ListBox, Select, Tooltip } from "@heroui/react";
import {
  Activity,
  Building2,
  ChevronDown,
  Database,
  LockKeyhole,
  ShieldCheck,
  Zap,
} from "lucide-react";

export default function TenantSidebar({ tenant, tenants, onTenantChange }) {
  return (
    <aside className="hidden w-80 shrink-0 border-r border-border/70 bg-surface/82 px-4 py-5 backdrop-blur-xl lg:block">
      <div className="flex h-full flex-col gap-5">
        <div className="flex items-center gap-3 px-1">
          <div className="grid size-11 place-items-center rounded-lg bg-accent text-accent-foreground shadow-sm">
            <Building2 size={21} />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold">TDSE Platform</p>
            <p className="truncate text-xs text-muted">Cloud-native mental health</p>
          </div>
        </div>

        <Select
          className="w-full"
          onChange={onTenantChange}
          placeholder="Tenant"
          value={tenant.id}
          variant="secondary"
        >
          <Label>Organizacion activa</Label>
          <Select.Trigger>
            <Select.Value />
            <Select.Indicator>
              <ChevronDown size={16} />
            </Select.Indicator>
          </Select.Trigger>
          <Select.Popover>
            <ListBox>
              {tenants.map((item) => (
                <ListBox.Item id={item.id} key={item.id} textValue={item.name}>
                  <div className="flex w-full items-center justify-between gap-3">
                    <span className="font-medium">{item.name}</span>
                    <Chip color="accent" size="sm" variant="soft">
                      {item.shortName}
                    </Chip>
                  </div>
                  <ListBox.ItemIndicator />
                </ListBox.Item>
              ))}
            </ListBox>
          </Select.Popover>
        </Select>

        <Card className="rounded-lg border border-border/70" variant="secondary">
          <Card.Header>
            <Card.Title className="text-base">{tenant.name}</Card.Title>
            <Card.Description>{tenant.domain}</Card.Description>
          </Card.Header>
          <Card.Content className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {tenant.departments.map((department) => (
                <Chip key={department} color="default" size="sm" variant="secondary">
                  {department}
                </Chip>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <TenantMetric label="Miembros" value={tenant.members} />
              <TenantMetric label="Hoy" value={tenant.analysesToday} />
            </div>
          </Card.Content>
        </Card>

        <nav className="space-y-2">
          <SidebarButton icon={Activity} label="Analisis" isActive />
          <SidebarButton icon={Database} label="Resultados" />
          <SidebarButton icon={ShieldCheck} label="Gobierno" />
        </nav>

        <div className="mt-auto space-y-3">
          <div className="rounded-lg border border-border/70 bg-surface-secondary/72 p-3">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <LockKeyhole size={16} />
                Aislamiento
              </div>
              <Chip color="success" size="sm" variant="soft">
                {tenant.compliance}
              </Chip>
            </div>
            <p className="break-all text-xs leading-5 text-muted">{tenant.id}</p>
          </div>

          <Tooltip>
            <Tooltip.Trigger>
              <Button className="w-full justify-start" variant="outline">
                <Zap size={17} />
                AWS pipeline activo
              </Button>
            </Tooltip.Trigger>
            <Tooltip.Content showArrow>
              <Tooltip.Arrow />
              {tenant.region}
            </Tooltip.Content>
          </Tooltip>
        </div>
      </div>
    </aside>
  );
}

function TenantMetric({ label, value }) {
  return (
    <div className="rounded-md border border-border/70 bg-surface px-3 py-2">
      <p className="text-xs text-muted">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}

function SidebarButton({ icon: Icon, label, isActive = false }) {
  return (
    <Button
      className={`w-full justify-start ${isActive ? "bg-accent-soft text-accent-soft-foreground" : ""}`}
      variant={isActive ? "tertiary" : "ghost"}
    >
      <Icon size={17} />
      {label}
    </Button>
  );
}
