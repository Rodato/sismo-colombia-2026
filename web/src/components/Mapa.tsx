"use client";

import { geoMercator, geoPath } from "d3-geo";
import { useEffect, useMemo, useRef, useState } from "react";
import { CAPAS, Capa, Props, RAMPA, paso } from "@/lib/capas";

type Feature = { type: "Feature"; properties: Props; geometry: never };
type FC = { type: "FeatureCollection"; features: Feature[] };

const W = 820;
const H = 900;

export default function Mapa() {
  const [fc, setFc] = useState<FC | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [capaId, setCapaId] = useState(CAPAS[0].id);
  const [hover, setHover] = useState<{ p: Props; x: number; y: number } | null>(null);
  const [sel, setSel] = useState<Props | null>(null);
  const [busca, setBusca] = useState("");
  const svgRef = useRef<SVGSVGElement>(null);

  const capa = CAPAS.find((c) => c.id === capaId)!;

  useEffect(() => {
    fetch("/data/municipios.geojson")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setFc)
      .catch((e) => setError(String(e)));
  }, []);

  const { paths, proj } = useMemo(() => {
    if (!fc) return { paths: [], proj: null };
    const projection = geoMercator().fitSize([W, H], fc as never);
    const gp = geoPath(projection);
    return {
      paths: fc.features.map((f) => ({ d: gp(f as never) ?? "", p: f.properties })),
      proj: projection,
    };
  }, [fc]);

  // Coincidencias de búsqueda: se resaltan con un anillo, no con color de relleno,
  // para no romper la codificación secuencial de la capa activa.
  const resaltados = useMemo(() => {
    const q = busca.trim().toLowerCase();
    if (q.length < 2) return new Set<string>();
    return new Set(
      paths
        .filter(
          ({ p }) =>
            p.municipio.toLowerCase().includes(q) || p.departamento.toLowerCase().includes(q),
        )
        .map(({ p }) => p.divipola),
    );
  }, [busca, paths]);

  if (error)
    return (
      <div className="card p-6 text-sm" style={{ color: "var(--critical)" }}>
        No se pudo cargar la capa municipal: {error}
      </div>
    );

  if (!fc)
    return (
      <div className="card grid place-items-center" style={{ height: 420 }}>
        <span className="text-sm" style={{ color: "var(--text-muted)" }}>
          Cargando 682 municipios…
        </span>
      </div>
    );

  return (
    <div>
      {/* filtros en una fila, encima del gráfico */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {CAPAS.map((c) => {
          const activa = c.id === capaId;
          return (
            <button
              key={c.id}
              onClick={() => setCapaId(c.id)}
              className="rounded-md px-3 py-1.5 text-sm transition-colors"
              style={{
                background: activa ? "var(--text-primary)" : "var(--surface-1)",
                color: activa ? "var(--surface-1)" : "var(--text-secondary)",
                border: `1px solid ${activa ? "var(--text-primary)" : "var(--border)"}`,
              }}
              aria-pressed={activa}
            >
              {c.nombre}
            </button>
          );
        })}
        <input
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar municipio…"
          className="ml-auto rounded-md px-3 py-1.5 text-sm outline-none"
          style={{
            background: "var(--surface-1)",
            border: "1px solid var(--border)",
            color: "var(--text-primary)",
            minWidth: 200,
          }}
        />
      </div>

      <p className="mb-4 max-w-3xl text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
        {capa.descripcion}
      </p>

      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="card scroll-x relative p-2">
          <svg
            ref={svgRef}
            viewBox={`0 0 ${W} ${H}`}
            className="h-auto w-full"
            style={{ maxWidth: "100%" }}
            role="img"
            aria-label={`Mapa de municipios de Colombia coloreado por ${capa.nombre}`}
            onMouseLeave={() => setHover(null)}
          >
            {paths.map(({ d, p }) => {
              const s = paso(p[capa.campo] as number, capa);
              const resaltado = resaltados.has(p.divipola);
              const seleccionado = sel?.divipola === p.divipola;
              return (
                <path
                  key={p.divipola}
                  d={d}
                  fill={s == null ? "var(--grid)" : RAMPA[s]}
                  stroke={
                    seleccionado
                      ? "var(--text-primary)"
                      : resaltado
                        ? "var(--series-2)"
                        : "var(--surface-1)"
                  }
                  strokeWidth={seleccionado ? 2 : resaltado ? 1.5 : 0.3}
                  style={{ cursor: "pointer" }}
                  onMouseEnter={(e) => {
                    const r = svgRef.current?.getBoundingClientRect();
                    setHover({
                      p,
                      x: r ? e.clientX - r.left : 0,
                      y: r ? e.clientY - r.top : 0,
                    });
                  }}
                  onClick={() => setSel(p)}
                >
                  <title>{`${p.municipio}, ${p.departamento}`}</title>
                </path>
              );
            })}
            {/* epicentro */}
            {proj &&
              (() => {
                const xy = proj([-76.2422, 4.8436]);
                if (!xy) return null;
                return (
                  <g pointerEvents="none">
                    <circle cx={xy[0]} cy={xy[1]} r={7} fill="none" stroke="var(--surface-1)" strokeWidth={3} />
                    <circle cx={xy[0]} cy={xy[1]} r={7} fill="none" stroke="var(--critical)" strokeWidth={2} />
                    <circle cx={xy[0]} cy={xy[1]} r={2} fill="var(--critical)" />
                  </g>
                );
              })()}
          </svg>

          {hover && (
            <div
              className="pointer-events-none absolute z-10 rounded-md px-3 py-2 text-xs shadow-lg"
              style={{
                left: Math.min(hover.x + 14, W - 190),
                top: hover.y + 14,
                background: "var(--surface-1)",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
                minWidth: 170,
              }}
            >
              <div className="font-semibold">{hover.p.municipio}</div>
              <div style={{ color: "var(--text-muted)" }}>{hover.p.departamento}</div>
              <div className="mt-1.5 tnum">
                {capa.nombre}:{" "}
                <strong>{capa.formato(hover.p[capa.campo] as number)}</strong>{" "}
                <span style={{ color: "var(--text-muted)" }}>{capa.unidad}</span>
              </div>
              <div className="tnum" style={{ color: "var(--text-secondary)" }}>
                {hover.p.pob_total.toLocaleString("es-CO")} habitantes
              </div>
            </div>
          )}

          <Leyenda capa={capa} />
        </div>

        <Ficha p={sel} onCerrar={() => setSel(null)} />
      </div>
    </div>
  );
}

function Leyenda({ capa }: { capa: Capa }) {
  // Capas ordinales: una muestra por nivel, con su nombre. La rampa completa de
  // 7 pasos aquí no significa nada — solo 3 de sus escalones se usan.
  if (capa.niveles) {
    return (
      <div className="mt-2 px-2 pb-1">
        <div className="mb-1.5 text-xs" style={{ color: "var(--text-muted)" }}>
          {capa.nombre}
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1.5">
          {capa.niveles.map((n) => (
            <div key={n.etiqueta} className="flex items-center gap-1.5">
              <div
                style={{
                  background: RAMPA[n.paso],
                  width: 12,
                  height: 12,
                  borderRadius: 2,
                  border: "1px solid var(--border)",
                }}
              />
              <span className="text-[11px]" style={{ color: "var(--text-secondary)" }}>
                {n.etiqueta}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Cada muestra de la rampa corresponde a una cubeta, y en las capas
  // invertidas el orden se voltea. Se calcula la cubeta real de cada muestra
  // en vez de suponer que van alineadas: con 6 cortes y 7 muestras, suponerlo
  // desplaza todas las etiquetas una posición.
  const c = capa.cortes!;
  const etiqueta = (bucket: number) =>
    bucket === 0
      ? `<${capa.formato(c[0])}`
      : bucket > c.length - 1
        ? `≥${capa.formato(c[c.length - 1])}`
        : capa.formato(c[bucket - 1]);
  const bucketDe = (j: number) => (capa.invertida ? c.length - j : j);

  return (
    <div className="mt-2 px-2 pb-1">
      <div className="mb-1 text-xs" style={{ color: "var(--text-muted)" }}>
        {capa.nombre} ({capa.unidad})
        {capa.invertida ? " — más oscuro = suelo más blando" : ""}
      </div>
      <div className="flex items-stretch gap-[2px]">
        {RAMPA.map((color, j) => (
          <div key={j} className="flex-1">
            <div style={{ background: color, height: 10, borderRadius: 2 }} />
            <div className="tnum mt-1 text-[10px]" style={{ color: "var(--text-muted)" }}>
              {etiqueta(bucketDe(j))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Ficha({ p, onCerrar }: { p: Props | null; onCerrar: () => void }) {
  if (!p)
    return (
      <div className="card p-5">
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Pasa el cursor por un municipio para ver su dato, o haz clic para fijar su ficha
          completa aquí.
        </p>
      </div>
    );

  const filas: [string, string][] = [
    ["Intensidad máxima", `${p.mmi_max.toFixed(1)} MMI`],
    ["Intensidad media", `${p.mmi_media.toFixed(1)} MMI`],
    ["Suelo (Vs30)", `${p.vs30_medio.toFixed(0)} m/s`],
    ["Población 2026", p.pob_total.toLocaleString("es-CO")],
    ["— en cabecera", p.pob_cabecera.toLocaleString("es-CO")],
    ["— rural disperso", p.pob_rural.toLocaleString("es-CO")],
    ["Vivienda vulnerable", `${p.def_cualitativo?.toFixed(0) ?? "—"}%`],
    ["Licuefacción máx.", p.licuef_max?.toFixed(2) ?? "—"],
    ["Deslizamiento máx.", p.desliz_max?.toFixed(3) ?? "—"],
    ["Menciones en prensa", `${p.menciones} (${p.menciones_nacional} nal. / ${p.menciones_regional} reg.)`],
    ["Puesto por exposición", `#${p.rank} de 682`],
  ];

  // Solo 5 municipios tienen cifra propia. Para el resto no se muestra "0"
  // sino nada, porque cero muertos reportados y ningún reporte no son lo mismo:
  // Armenia sí reportó cero.
  if (p.cobertura_dato === 2) {
    filas.push(
      ["Muertos reportados", p.muertos_rep?.toLocaleString("es-CO") ?? "—"],
      ["— por 100 mil hab.", p.muertos_100k?.toFixed(1) ?? "—"],
      ["Heridos reportados", p.heridos_rep?.toLocaleString("es-CO") ?? "—"],
      ["Desaparecidos", p.desaparecidos_rep?.toLocaleString("es-CO") ?? "—"],
    );
  }

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-lg font-semibold leading-tight">{p.municipio}</h3>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            {p.departamento}
          </p>
        </div>
        <button
          onClick={onCerrar}
          className="text-sm"
          style={{ color: "var(--text-muted)" }}
          aria-label="Cerrar ficha"
        >
          ✕
        </button>
      </div>
      <dl className="mt-4 space-y-1.5">
        {filas.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3 text-sm">
            <dt style={{ color: "var(--text-secondary)" }}>{k}</dt>
            <dd className="tnum font-medium">{v}</dd>
          </div>
        ))}
      </dl>
      {p.menciones === 0 && p.mmi_max >= 6 && (
        <p
          className="mt-4 rounded-md p-2 text-xs leading-relaxed"
          style={{ background: "var(--plane)", color: "var(--text-secondary)" }}
        >
          Sacudida de nivel de daño y ninguna mención en el corpus analizado. Eso indica
          ausencia del relato nacional — no prueba que ningún medio lo haya cubierto.
        </p>
      )}
      {p.cobertura_dato < 2 && p.mmi_max >= 6 && (
        <p
          className="mt-2 rounded-md p-2 text-xs leading-relaxed"
          style={{ background: "var(--plane)", color: "var(--text-secondary)" }}
        >
          No existe cifra pública de pérdidas para este municipio.{" "}
          {p.cobertura_dato === 1
            ? "Solo se publicó el agregado de su departamento."
            : "Ni siquiera hay agregado departamental."}{" "}
          La única fuente municipal cubre a las 5 ciudades capitales en alerta roja.
        </p>
      )}
    </div>
  );
}
