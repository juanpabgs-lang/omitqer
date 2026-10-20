import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { compact } from "../lib/format";
import { get } from "../lib/api";

const CHAPTERS = [
  { n: "01", to: "/socio", k: "Entrada", t: "El socio fotografía la factura y ve el monto." },
  { n: "02", to: "/prestador", k: "Red", t: "OMINT Directo: el médico cobra en 24 h." },
  { n: "03", to: "/integridad", k: "Dinero", t: "El mismo motor audita lo que factura la cartilla." },
  { n: "04", to: "/caso", k: "Prueba", t: "Cada peso tiene un evento confirmado en el ledger." },
  { n: "05", to: "/defensa", k: "Defensa", t: "Res. 951/2026: cinco días hábiles, silencio = culpa." },
  { n: "06", to: "/sap", k: "Encaje", t: "SAP S/4HANA por APIs liberadas. No se pelea el core." },
];

export function Hub() {
  const nav = useNavigate();
  const [roi, setRoi] = useState<any>(null);
  const [i, setI] = useState(0);

  useEffect(() => {
    get("/api/roi").then(setRoi).catch(() => setRoi(null));
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") {
        setI((x) => Math.min(CHAPTERS.length - 1, x + 1));
        nav(CHAPTERS[Math.min(CHAPTERS.length - 1, i + 1)].to);
      }
      if (e.key === "ArrowLeft") {
        setI((x) => Math.max(0, x - 1));
      }
      if (e.key === "1") nav("/socio");
      if (e.key === "2") nav("/prestador");
      if (e.key === "3") nav("/integridad");
      if (e.key === "4") nav("/caso");
      if (e.key === "5") nav("/defensa");
      if (e.key === "6") nav("/sap");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [i, nav]);

  const run = roi?.run_rate_ars ?? 5.5e9;

  return (
    <main>
      <section className="relative overflow-hidden bg-[#111318] text-[#f3f3f1]">
        <div className="pointer-events-none absolute inset-0 opacity-40" style={{ background: "radial-gradient(80% 60% at 20% 80%, #3a4654 0%, transparent 60%)" }} />
        <div className="relative mx-auto max-w-[1440px] px-[clamp(16px,5.4vw,104px)] py-28">
          <p className="rise text-[12px] uppercase tracking-[0.18em] text-white/50">
            OMINT · Villa Larroudet · 1967
          </p>
          <h1 className="rise mt-6 max-w-4xl text-[clamp(42px,7vw,92px)] font-normal leading-[0.95] tracking-[-0.035em]" style={{ animationDelay: "80ms" }}>
            Devolver en minutos. Quedarse con el médico. Demostrarlo en cinco días.
          </h1>
          <p className="rise mt-8 max-w-xl text-[19px] text-white/70" style={{ animationDelay: "140ms" }}>
            OSDE ya lee el QR. Swiss Medical ya valida contra ARCA. Eso no es una ventaja.
            La ventaja es una red que se paga sola, un mapa de precios verificados y un ledger
            que gana el expediente.
          </p>
          <div className="rise mt-10 flex gap-6 text-[13px]" style={{ animationDelay: "200ms" }}>
            <Link to="/socio" className="bg-mint px-5 py-2.5 text-ink">
              Ver el reintegro
            </Link>
            <Link to="/caso" className="border border-white/30 px-5 py-2.5">
              Ver el dinero
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1440px] px-[clamp(16px,5.4vw,104px)] py-20">
        <p className="text-[12px] uppercase tracking-[0.16em] text-mute">Run-rate simulado</p>
        <div className="mt-6 grid gap-10 md:grid-cols-3">
          <Stat k="Valor anual a defaults" v={compact(run)} s="Cada input es supuesto, fuente o medido" />
          <Stat k="P10 – P90" v={roi ? `${compact(roi.monte_carlo.p10)} · ${compact(roi.monte_carlo.p90)}` : "—"} s="800 sorteos sobre supuestos, no sobre fuentes" />
          <Stat k="Payback" v={roi?.payback_months ? `${roi.payback_months.toFixed(1)} meses` : "—"} s="USD 450k año 1, supuesto" />
        </div>
      </section>

      <div className="hairline" />

      <section className="mx-auto max-w-[1440px] px-[clamp(16px,5.4vw,104px)] py-20">
        <div className="grid gap-16 md:grid-cols-12">
          <div className="md:col-span-7">
            <p className="text-[12px] uppercase tracking-[0.16em] text-mute">Seis capítulos</p>
            <h2 className="mt-4 text-[clamp(32px,4vw,52px)] leading-[1.05] tracking-[-0.03em]">
              El reintegro es la puerta. El foso es lo que queda después.
            </h2>
          </div>
          <p className="self-end text-[15px] text-mute md:col-span-4 md:col-start-9">
            Flechas del teclado o teclas 1–6. Datos 100% sintéticos. Ningún socio real.
          </p>
        </div>
        <ol className="mt-14 divide-y divide-line">
          {CHAPTERS.map((c) => (
            <li key={c.n}>
              <Link to={c.to} className="grid grid-cols-[3rem_1fr_auto] items-baseline gap-6 py-5 hover:text-navy">
                <span className="text-[13px] text-mute">{c.n}</span>
                <span>
                  <span className="block text-[12px] uppercase tracking-[0.14em] text-mute">{c.k}</span>
                  <span className="text-[18px]">{c.t}</span>
                </span>
                <span className="text-[13px] text-mute">abrir</span>
              </Link>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}

function Stat({ k, v, s }: { k: string; v: string; s: string }) {
  return (
    <div>
      <div className="text-[12px] uppercase tracking-[0.14em] text-mute">{k}</div>
      <div className="mt-2 text-[28px] tracking-[-0.03em]">{v}</div>
      <div className="mt-2 text-[13px] text-mute">{s}</div>
    </div>
  );
}
