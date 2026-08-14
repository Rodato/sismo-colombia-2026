"use client";

type Corte = {
  fecha: string;
  corte: string;
  muertos: number | null;
  heridos: number | null;
  desaparecidos: number | null;
  fuente: string;
  url: string;
};

const SERIES = [
  { campo: "muertos" as const, nombre: "Muertos", color: "var(--series-1)" },
  { campo: "heridos" as const, nombre: "Heridos", color: "var(--series-2)" },
  { campo: "desaparecidos" as const, nombre: "Desaparecidos", color: "var(--series-3)" },
];

// Small multiples y no un solo gráfico: los tres conteos viven en escalas
// distintas (281 / 3.971 / 379) y superponerlos exigiría dos ejes verticales,
// que deforman la comparación. Un panel por serie, cada uno con su escala.
export default function SerieOficial({ serie }: { serie: Corte[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {SERIES.map((s) => {
        const puntos = serie
          .map((c, i) => ({ i, v: c[s.campo], etiqueta: `${c.fecha.slice(5)} ${c.corte}` }))
          .filter((p) => p.v != null) as { i: number; v: number; etiqueta: string }[];
        if (puntos.length < 2) return null;

        const W = 300;
        const H = 150;
        const M = { t: 18, r: 14, b: 26, l: 44 };
        const min = Math.min(...puntos.map((p) => p.v));
        const max = Math.max(...puntos.map((p) => p.v));
        const pad = (max - min) * 0.18 || 1;
        const y = (v: number) =>
          M.t + (H - M.t - M.b) * (1 - (v - (min - pad)) / (max + pad - (min - pad)));
        const x = (k: number) =>
          M.l + ((W - M.l - M.r) * k) / Math.max(1, puntos.length - 1);

        const d = puntos.map((p, k) => `${k ? "L" : "M"}${x(k)},${y(p.v)}`).join(" ");

        // marca los tramos en que la cifra BAJA: es el hallazgo
        const bajadas = puntos
          .map((p, k) => (k > 0 && p.v < puntos[k - 1].v ? k : -1))
          .filter((k) => k > 0);

        return (
          <figure key={s.campo} className="card p-3">
            <figcaption className="mb-1 flex items-baseline gap-2">
              <span
                aria-hidden
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 3,
                  background: s.color,
                  display: "inline-block",
                }}
              />
              <span className="text-sm font-semibold">{s.nombre}</span>
              <span className="tnum ml-auto text-xs" style={{ color: "var(--text-muted)" }}>
                {puntos[puntos.length - 1].v.toLocaleString("es-CO")}
              </span>
            </figcaption>
            <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img"
                 aria-label={`${s.nombre}: evolución entre cortes oficiales`}>
              <line x1={M.l} y1={H - M.b} x2={W - M.r} y2={H - M.b} stroke="var(--axis)" strokeWidth={1} />
              {[min, max].map((v) => (
                <g key={v}>
                  <line x1={M.l} y1={y(v)} x2={W - M.r} y2={y(v)} stroke="var(--grid)" strokeWidth={1} />
                  <text x={M.l - 6} y={y(v) + 3} textAnchor="end" className="tnum"
                        fontSize={10} fill="var(--text-muted)">
                    {v.toLocaleString("es-CO")}
                  </text>
                </g>
              ))}
              {/* tramos en descenso, resaltados */}
              {bajadas.map((k) => (
                <line key={k} x1={x(k - 1)} y1={y(puntos[k - 1].v)} x2={x(k)} y2={y(puntos[k].v)}
                      stroke="var(--critical)" strokeWidth={4} strokeLinecap="round" opacity={0.35} />
              ))}
              <path d={d} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" />
              {puntos.map((p, k) => (
                <circle key={k} cx={x(k)} cy={y(p.v)} r={4} fill={s.color}
                        stroke="var(--surface-1)" strokeWidth={2}>
                  <title>{`${p.etiqueta}: ${p.v.toLocaleString("es-CO")}`}</title>
                </circle>
              ))}
              <text x={M.l} y={H - 8} fontSize={9} fill="var(--text-muted)">
                {puntos[0].etiqueta}
              </text>
              <text x={W - M.r} y={H - 8} fontSize={9} fill="var(--text-muted)" textAnchor="end">
                {puntos[puntos.length - 1].etiqueta}
              </text>
            </svg>
            {bajadas.length > 0 && (
              <p className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>
                {bajadas.length === 1 ? "Un tramo en descenso" : `${bajadas.length} tramos en descenso`}:
                la cifra oficial baja entre un corte y el siguiente.
              </p>
            )}
          </figure>
        );
      })}
    </div>
  );
}
