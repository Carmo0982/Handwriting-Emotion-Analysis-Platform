export const tenants = [
  {
    id: "tenant-aurora-health",
    name: "Cl\u00ednica Aurora",
    shortName: "Aurora",
    domain: "salud mental",
    plan: "Plan cl\u00ednico",
    region: "us-east-1",
    members: 42,
    analysesToday: 128,
    riskQueue: 9,
    compliance: "Activo",
    departments: ["Psicolog\u00eda", "Psiquiatr\u00eda", "Bienestar"],
  },
  {
    id: "tenant-campus-andes",
    name: "Campus Andes",
    shortName: "Andes",
    domain: "bienestar universitario",
    plan: "Plan educativo",
    region: "us-east-1",
    members: 18,
    analysesToday: 76,
    riskQueue: 6,
    compliance: "Activo",
    departments: ["Orientaci\u00f3n", "Permanencia", "Salud"],
  },
  {
    id: "tenant-nova-people",
    name: "Nova People Ops",
    shortName: "Nova",
    domain: "bienestar laboral",
    plan: "Plan corporativo",
    region: "us-west-2",
    members: 27,
    analysesToday: 94,
    riskQueue: 11,
    compliance: "Activo",
    departments: ["Talento", "Riesgo", "Cultura"],
  },
];

export const emotionMeta = {
  ansiedad: {
    label: "Ansiedad",
    color: "danger",
    riskClass: "risk-ansiedad",
  },
  estres: {
    label: "Estr\u00e9s",
    color: "warning",
    riskClass: "risk-estres",
  },
  depresion: {
    label: "Depresi\u00f3n",
    color: "danger",
    riskClass: "risk-depresion",
  },
  neutro: {
    label: "Neutro",
    color: "success",
    riskClass: "risk-neutro",
  },
};

export const biomarkerLabels = {
  pressure: "Presi\u00f3n",
  rhythm: "Ritmo",
  slant: "Inclinaci\u00f3n",
  spacing: "Espaciado",
  strokeVariability: "Variabilidad",
};
