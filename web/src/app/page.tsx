import fs from "node:fs";
import path from "node:path";
import Mapa from "@/components/Mapa";
import SerieOficial from "@/components/SerieOficial";

type Resumen = {
  evento: Record<string, string | number>;
  alcance: Record<string, number>;
  cobertura: Record<string, number>;
  danos: Record<string, number>;
  serie: never[];
  pager: Record<string, number | string>;
  cinturon_suelo_blando: {
    municipio: string; departamento: string; vs30: number; mmi: number;
    pob: number; licuef: number; menciones: number;
  }[];
  corredor_choco: {
    municipio: string; mmi: number; licuef_km2: number; pob: number;
    deficit: number; menciones: number;
  }[];
  mas_mencionados: { municipio: string; departamento: string; menciones: number; mmi: number }[];
  fuentes: Record<string, string>;
};

function leerResumen(): Resumen {
  const p = path.join(process.cwd(), "public", "data", "resumen.json");
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

const nf = (v: number) => v.toLocaleString("es-CO");

export default function Page() {
  const r = leerResumen();

  const tiles = [
    { v: nf(r.alcance.municipios_mmi6), l: "municipios con sacudida de nivel de daño", s: "MMI VI o más" },
    { v: `${(r.alcance.poblacion_mmi6 / 1e6).toFixed(1)} M`, l: "personas viven en ellos", s: "proyección DANE 2026" },
    { v: nf(r.cobertura.municipios_con_mencion), l: "aparecen en la cobertura analizada", s: `de ${nf(r.cobertura.municipios_sacudidos)}` },
    { v: `${r.cobertura.concentracion_top10_pct}%`, l: "de las menciones se las llevan 10 municipios", s: "corpus de 199 notas" },
  ];

  return (
    <main className="mx-auto max-w-6xl px-5 py-12 md:py-16">
      <header className="mb-12">
        <p className="mb-3 text-sm uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
          Colombia · 10 de agosto de 2026 · magnitud 7,4
        </p>
        <h1 className="text-4xl font-bold leading-tight md:text-5xl">
          El sismo que no se contó
        </h1>
        <p className="mt-5 max-w-3xl text-lg leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          El terremoto de San José del Palmar sacudió{" "}
          <strong style={{ color: "var(--text-primary)" }}>{nf(r.alcance.municipios_mmi6)} municipios</strong>{" "}
          con intensidad suficiente para dañar edificaciones. La cobertura se concentró en diez.
          Este mapa cruza la sacudida real medida por el USGS con quién vive debajo y en qué
          tipo de vivienda, para mostrar dónde hay daño que nadie fue a mirar.
        </p>
      </header>

      <section className="mb-14 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map((t) => (
          <div key={t.l} className="card p-5">
            <div className="tnum text-3xl font-semibold">{t.v}</div>
            <div className="mt-1.5 text-sm leading-snug" style={{ color: "var(--text-secondary)" }}>
              {t.l}
            </div>
            <div className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
              {t.s}
            </div>
          </div>
        ))}
      </section>

      <section className="mb-16">
        <h2 className="mb-1 text-2xl font-semibold">El mapa</h2>
        <p className="mb-5 text-sm" style={{ color: "var(--text-muted)" }}>
          682 municipios dentro de la huella del sismo. El círculo rojo marca el epicentro.
        </p>
        <Mapa />
      </section>

      <section className="mb-16">
        <h2 className="mb-1 text-2xl font-semibold">El suelo decide más que la distancia</h2>
        <p className="mb-5 max-w-3xl text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          El epicentro estuvo en el Chocó, pero la ciudad más golpeada fue Pereira, a más de
          100 km. La razón está en el suelo: donde es blando, amplifica la onda como una
          gelatina. Hay un cinturón de suelo blando en el norte del Cauca y el valle del río
          Cauca —terreno aluvial de caña— que recibió sacudida de nivel de daño lejos del
          epicentro. La probabilidad de licuefacción, calculada con un modelo independiente,
          lo confirma.
        </p>
        <div className="card scroll-x">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Municipio", "Depto.", "Vs30", "MMI", "Licuefacción", "Habitantes", "Menciones"].map((h, i) => (
                  <th key={h} className={`px-4 py-3 font-medium ${i > 1 ? "text-right" : "text-left"}`}
                      style={{ color: "var(--text-muted)" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {r.cinturon_suelo_blando.map((m) => (
                <tr key={m.municipio} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td className="px-4 py-2.5 font-medium">{m.municipio}</td>
                  <td className="px-4 py-2.5" style={{ color: "var(--text-secondary)" }}>{m.departamento}</td>
                  <td className="tnum px-4 py-2.5 text-right">{m.vs30} m/s</td>
                  <td className="tnum px-4 py-2.5 text-right">{m.mmi}</td>
                  <td className="tnum px-4 py-2.5 text-right">{m.licuef}</td>
                  <td className="tnum px-4 py-2.5 text-right">{nf(m.pob)}</td>
                  <td className="tnum px-4 py-2.5 text-right"
                      style={{ color: m.menciones === 0 ? "var(--critical)" : "var(--text-primary)" }}>
                    {m.menciones}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
          Vs30 por debajo de 300 m/s indica suelo blando. Son municipios mayoritariamente
          afrodescendientes y de bajos ingresos del norte del Cauca.
        </p>
      </section>

      <section className="mb-16">
        <h2 className="mb-1 text-2xl font-semibold">El corredor fluvial del Chocó</h2>
        <p className="mb-5 max-w-3xl text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          Los municipios ribereños del Atrato, el San Juan y el Baudó acumulan las tres cosas
          a la vez: sacudida fuerte, la mayor superficie con licuefacción probable del país y
          un parque de vivienda que el censo clasifica casi entero en déficit. Es donde menos
          capacidad hay de absorber el golpe.
        </p>
        <div className="card scroll-x">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Municipio", "MMI", "Área con licuefacción", "Déficit de vivienda", "Habitantes", "Menciones"].map((h, i) => (
                  <th key={h} className={`px-4 py-3 font-medium ${i ? "text-right" : "text-left"}`}
                      style={{ color: "var(--text-muted)" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {r.corredor_choco.map((m) => (
                <tr key={m.municipio} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td className="px-4 py-2.5 font-medium">{m.municipio}</td>
                  <td className="tnum px-4 py-2.5 text-right">{m.mmi}</td>
                  <td className="tnum px-4 py-2.5 text-right">{nf(m.licuef_km2)} km²</td>
                  <td className="tnum px-4 py-2.5 text-right">{m.deficit}%</td>
                  <td className="tnum px-4 py-2.5 text-right">{nf(m.pob)}</td>
                  <td className="tnum px-4 py-2.5 text-right"
                      style={{ color: m.menciones === 0 ? "var(--critical)" : "var(--text-primary)" }}>
                    {m.menciones}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-16">
        <h2 className="mb-1 text-2xl font-semibold">Un conteo que no converge</h2>
        <p className="mb-5 max-w-3xl text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          Entre el 12 y el 13 de agosto el número oficial de desaparecidos sube de 287 a 496 y
          vuelve a bajar a 377; el de heridos baja de 3.755 a 3.494. Un conteo que se mueve en
          los dos sentidos no se está corrigiendo con información nueva: refleja que no hay un
          registro único. Es exactamente lo que denunció la Defensoría del Pueblo el 13 de
          agosto al advertir que no existe censo de damnificados.
        </p>
        <SerieOficial serie={r.serie} />
        <p className="mt-4 max-w-3xl text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          Para dimensionar la incertidumbre: el modelo PAGER del USGS, calibrado con sismos
          históricos, estimó una mediana de{" "}
          <strong style={{ color: "var(--text-primary)" }}>{nf(r.pager.mediana_muertos as number)} muertos</strong>{" "}
          para un evento de estas características. El conteo oficial va en 281 más 379
          desaparecidos. PAGER es un modelo, no un conteo, y su intervalo es ancho: la brecha
          no prueba subregistro. Lo que muestra es cuánta incertidumbre sigue abierta mientras
          no exista el censo.
        </p>
      </section>

      <section className="mb-16">
        <h2 className="mb-1 text-2xl font-semibold">Cómo se hizo</h2>
        <div className="card mt-4 p-6 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          <p className="mb-4">
            La intensidad viene del ShakeMap del USGS (evento us6000tjl2, versión 6): una
            grilla de 685×683 celdas de ~1 km con intensidad Mercalli, aceleración y velocidad
            de onda del suelo. Esa grilla se cruzó con los polígonos municipales del Marco
            Geoestadístico Nacional del DANE, la proyección de población municipal a 2026 y el
            déficit habitacional del censo de 2018.
          </p>
          <p className="mb-4">
            <strong style={{ color: "var(--text-primary)" }}>Lo que el índice no es.</strong>{" "}
            El índice de exposición combina sacudida, población y vulnerabilidad de vivienda
            para priorizar dónde mirar. No es un modelo de pérdidas ni una estimación de
            víctimas. Su validación es que ubica a Pereira en primer lugar sin usar ningún dato
            de muertos.
          </p>
          <p className="mb-4">
            <strong style={{ color: "var(--text-primary)" }}>Lo que la medición de prensa no prueba.</strong>{" "}
            El conteo de menciones se hizo sobre un corpus de 199 notas de 11 medios,
            desambiguando homónimos y descartando menús de navegación y módulos de
            &ldquo;otras noticias&rdquo;. Ese corpus demuestra presencia, no ausencia: que un
            municipio no aparezca significa que está fuera del relato que ese corpus recoge,
            no que ningún medio lo haya cubierto. Verificaciones puntuales confirmaron que
            varios municipios sin menciones sí tenían cobertura en su prensa regional. Por eso
            la afirmación de esta pieza es sobre <em>concentración</em> del relato, no sobre
            silencio absoluto.
          </p>
          <p>
            <strong style={{ color: "var(--text-primary)" }}>Una corrección.</strong> La primera
            versión midió vulnerabilidad solo con el déficit cualitativo, y eso subestimaba
            gravemente al Chocó: allí la vivienda es tan precaria que el censo la clasifica
            como déficit cuantitativo. El indicador que se usa aquí es el déficit habitacional
            total.
          </p>
        </div>

        <div className="card mt-4 p-6">
          <h3 className="mb-3 text-sm font-semibold">Fuentes</h3>
          <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
            {Object.entries(r.fuentes).map(([k, v]) => (
              <div key={k}>
                <dt className="font-medium capitalize">{k.replace(/_/g, " ")}</dt>
                <dd style={{ color: "var(--text-secondary)" }}>{v}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 text-sm" style={{ color: "var(--text-secondary)" }}>
            Los datos procesados se pueden descargar como{" "}
            <a href="/data/municipios.csv" className="underline" style={{ color: "var(--series-1)" }}>
              CSV de 682 municipios
            </a>{" "}
            o{" "}
            <a href="/data/municipios.geojson" className="underline" style={{ color: "var(--series-1)" }}>
              GeoJSON
            </a>
            .
          </p>
        </div>
      </section>

      <footer className="border-t pt-6 text-sm" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
        <p>
          Análisis y visualización:{" "}
          <a href="https://danielotero.dev" className="underline" style={{ color: "var(--text-secondary)" }}>
            Daniel Otero
          </a>
          . Datos públicos del USGS y el DANE. Cifras oficiales con corte del 13 de agosto de 2026.
        </p>
      </footer>
    </main>
  );
}
