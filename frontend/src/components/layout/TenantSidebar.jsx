import { Card, Chip, Label, ListBox, Select } from "@heroui/react";
import { Building2, ChevronDown } from "lucide-react";

export default function TenantSidebar({ tenant, tenants, onTenantChange }) {
  return (
    <aside className="hidden w-80 shrink-0 border-r border-border/70 bg-surface/82 px-4 py-5 backdrop-blur-xl lg:block">
      <div className="flex h-full flex-col gap-5">
        <div className="flex items-center gap-3 px-1">
          <div className="grid size-11 place-items-center rounded-lg bg-accent text-accent-foreground shadow-sm">
            <Building2 size={21} />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold">MentalTrace AI</p>
            <p className="truncate text-xs text-muted">Salud mental para todos</p>
          </div>
        </div>

        <Select
          className="w-full"
          onSelectionChange={(key) => onTenantChange(String(key))}
          placeholder="Organización"
          selectedKey={tenant.id}
          variant="secondary"
        >
          <Label>Organización activa</Label>
          <Select.Trigger>
            <Select.Value />
            <Select.Indicator>
              <ChevronDown size={16} />
            </Select.Indicator>
          </Select.Trigger>
          <Select.Popover>
            <ListBox>
              {tenants.map((item) => (
                <ListBox.Item className="pr-7" id={item.id} key={item.id} textValue={item.name}>
                  <div className="flex w-full items-center justify-between gap-3">
                    <span className="font-medium">{item.name}</span>
                    <Chip color="accent" size="sm" variant="soft">
                      {item.shortName}
                    </Chip>
                  </div>
                  <ListBox.ItemIndicator className="ml-2" />
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
          <Card.Content>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <TenantMetric label="Miembros" value={tenant.members} />
              <TenantMetric label="Hoy" value={tenant.analysesToday} />
            </div>
          </Card.Content>
        </Card>
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

