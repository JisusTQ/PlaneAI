import { useApp } from "../lib/AppContext.jsx";

const TEXTOS = {
  verificando: { corto: "Conectando", largo: "Conectando con el servidor…" },
  despertando: { corto: "Despertando", largo: "El servidor se está activando; puede tardar hasta un minuto." },
  ok: { corto: "En línea", largo: "Conectado. Pensum y cupos se consultan en vivo en los portales de la UdeA." },
  caido: { corto: "Sin conexión", largo: "No hay conexión con el servidor. Revisa tu internet o intenta más tarde." },
};

export default function EstadoServidor({ compacto = false }) {
  const { servidor } = useApp();
  const t = TEXTOS[servidor];
  return (
    <span className={`estado-srv ${servidor}`} title={t.largo} role="status" aria-live="polite">
      <i aria-hidden />
      {compacto ? t.corto : t.corto}
    </span>
  );
}
