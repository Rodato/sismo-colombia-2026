export type Props = {
  divipola: string;
  municipio: string;
  departamento: string;
  mmi_max: number;
  mmi_media: number;
  vs30_medio: number;
  pob_total: number;
  pob_cabecera: number;
  pob_rural: number;
  def_cualitativo: number;
  def_habitacional: number;
  menciones: number;
  menciones_nacional: number;
  menciones_regional: number;
  indice: number;
  rank: number;
  desliz_max: number;
  desliz_km2: number;
  licuef_max: number;
  licuef_km2: number;
  licuef_frac: number;
};

export type Capa = {
  id: string;
  nombre: string;
  campo: keyof Props;
  descripcion: string;
  /** Cortes de la escala. El último es el tope; valores mayores caen en el último paso. */
  cortes: number[];
  /** true si un valor BAJO es el caso severo (p. ej. suelo blando). */
  invertida?: boolean;
  formato: (v: number) => string;
  unidad: string;
};

const num = (d = 0) => (v: number) =>
  v == null || Number.isNaN(v) ? "—" : v.toLocaleString("es-CO", { maximumFractionDigits: d, minimumFractionDigits: d });

const pct = (v: number) => (v == null || Number.isNaN(v) ? "—" : `${v.toFixed(0)}%`);

export const CAPAS: Capa[] = [
  {
    id: "mmi",
    nombre: "Intensidad de la sacudida",
    campo: "mmi_max",
    descripcion:
      "Escala de Mercalli modificada: qué tan fuerte se movió el suelo donde vive la gente. El daño estructural empieza alrededor de VI y se vuelve severo en VIII.",
    cortes: [4.5, 5.5, 6, 6.5, 7, 7.5],
    formato: num(1),
    unidad: "MMI",
  },
  {
    id: "suelo",
    nombre: "Dureza del suelo (Vs30)",
    campo: "vs30_medio",
    descripcion:
      "Velocidad de onda de corte en los 30 m superiores. Por debajo de ~300 m/s el suelo es blando y amplifica la sacudida como una gelatina: es lo que explica que Pereira sufriera más que municipios más cercanos al epicentro.",
    cortes: [250, 300, 400, 550, 700, 800],
    invertida: true,
    formato: num(0),
    unidad: "m/s",
  },
  {
    id: "vulnerabilidad",
    nombre: "Vivienda vulnerable",
    campo: "def_habitacional",
    descripcion:
      "Hogares en déficit habitacional total según el censo de 2018 — la suma del cualitativo (la vivienda necesita mejoras) y el cuantitativo (necesita reemplazo). Se usa el total y no solo el cualitativo a propósito: en el Chocó rural la vivienda es tan precaria que el DANE la cuenta como déficit cuantitativo, así que mirar solo el cualitativo hacía aparecer a Alto Baudó con 3% de vulnerabilidad cuando su déficit real es del 99,6%.",
    cortes: [20, 35, 50, 65, 80, 92],
    formato: pct,
    unidad: "% hogares",
  },
  {
    id: "indice",
    nombre: "Exposición combinada",
    campo: "indice",
    descripcion:
      "Sacudida × población × vulnerabilidad de vivienda. Es un índice de TAMIZAJE para priorizar dónde mirar, no una estimación de daños ni de víctimas. Valida contra la realidad: Pereira sale primero sin que el cálculo sepa nada de muertos.",
    cortes: [5e3, 5e4, 2e5, 8e5, 2e6, 6e6],
    formato: num(0),
    unidad: "índice",
  },
  {
    id: "licuefaccion",
    nombre: "Licuefacción probable",
    campo: "licuef_max",
    descripcion:
      "Probabilidad de que el suelo saturado pierda consistencia y se comporte como líquido (modelo Zhu 2017 del USGS). Marca el corredor fluvial del Chocó y el valle del río Cauca.",
    cortes: [0.05, 0.12, 0.2, 0.28, 0.35, 0.42],
    formato: (v) => (v == null ? "—" : v.toFixed(2)),
    unidad: "prob.",
  },
  {
    id: "cobertura",
    nombre: "Menciones en prensa",
    campo: "menciones",
    descripcion:
      "Veces que el municipio es nombrado en un corpus de 199 notas de 11 medios. Mide la CONCENTRACIÓN del relato, no la ausencia de cobertura: el corpus prueba presencia, no demuestra que nadie más haya informado.",
    cortes: [1, 2, 5, 12, 30, 80],
    formato: num(0),
    unidad: "menciones",
  },
];

/**
 * Índice de paso (0..RAMPA.length-1) de la rampa secuencial para un valor.
 *
 * N cortes producen N+1 cubetas, así que `cortes` debe tener exactamente
 * RAMPA.length-1 entradas. El clamp final es una red de seguridad: sin él, un
 * corte de más devuelve un índice fuera de la rampa, el fill queda en
 * `undefined` y el SVG pinta el municipio de negro — que fue exactamente lo
 * que pasó con los de intensidad más alta, los que más importan.
 */
export function paso(v: number | null | undefined, capa: Capa): number | null {
  if (v == null || Number.isNaN(v)) return null;
  const c = capa.cortes;
  let i = 0;
  while (i < c.length && v >= c[i]) i++;
  const idx = capa.invertida ? c.length - i : i;
  return Math.max(0, Math.min(RAMPA.length - 1, idx));
}

export const RAMPA = [
  "var(--seq-0)",
  "var(--seq-1)",
  "var(--seq-2)",
  "var(--seq-3)",
  "var(--seq-4)",
  "var(--seq-5)",
  "var(--seq-6)",
];
