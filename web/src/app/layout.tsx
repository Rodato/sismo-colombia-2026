import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "El sismo que no se contó — Colombia, 10 de agosto de 2026",
  description:
    "208 municipios sufrieron sacudida de nivel de daño. La cobertura se concentró en diez. Mapa de intensidad, suelo, vulnerabilidad de vivienda y atención mediática, con datos del USGS y el DANE.",
  openGraph: {
    title: "El sismo que no se contó",
    description:
      "208 municipios con sacudida de daño, 11,1 millones de personas expuestas y un conteo oficial que oscila.",
    locale: "es_CO",
    type: "article",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-CO">
      <body>{children}</body>
    </html>
  );
}
