import { useEffect, useState } from "react";
import { ars, compact, pct } from "../lib/format";
import { get, post } from "../lib/api";

const TABS = ["valor", "traba", "bajas", "mercado"] as const;

export function Direccion() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("valor");
  const [valor, setValor] = useState<any>(null);
  const [stalls, setStalls] = useState<any>(null);
  const [churn, setChurn] = useState<any>(null);
  const [mercado, setMercado] = useState<any>(null);
  const [sim, setSim] = useState<any>(null);
  const [tope, setTope] = useState(55000);

  useEffect(() => {
    get("/api/ledger/valor").then(setValor);
    get("/api/direccion/stalls").then(setStalls);
    get("/api/direccion/churn").then(setChurn);
    get("/api/mercado").then(setMercado);
  }, []);

  return (
    <main className="mx-auto max-w-[1440px] px-[clamp(16px,5.4vw,104px)] py-16">
      <p className="text-[12px] uppercase tracking-[0.16em] text-mute">Dirección</p>
      <h1 className="mt-3 text-[clamp(32px,4vw,48px)] tracking-[-0.03em]">Dónde se traba, por qué se van, cuánto vale.</h1>
      <div className="mt-8 flex gap-6 text-[13px]">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)} className={tab === t ? "underline decoration-mint underline-offset-4" : "text-mute"}>
            {t === "valor" ? "Valor" : t === "traba" ? "Dónde se traba" : t === "bajas" ? "Por qué se van" : "Mercado"}
          </button>
        ))}
      </div>

      {tab === "valor" && valor && (
        <section className="mt-10">
          <div className="text-[13px] text-mute">{valor.totals.rule}</div>
          <div className="mt-4 text-[32px]">{compact(valor.totals.confirmado_ars)} confirmado</div>
          <div className="text-[15px] text-mute">{compact(valor.totals.propuesto_ars)} propuesto</div>
          <div className="mt-2 text-[12px] text-mute">Cadena {valor.chain.ok ? "íntegra" : "rota"} · {valor.chain.events} eventos</div>
          <ul className="mt-8 divide-y divide-line text-[13px]">
            {valor.recent.map((e: any) => (
              <li key={e.id} className="flex justify-between py-2">
                <span>{e.kind} · {e.status}</span>
                <span>{ars(e.ars)} · {e.evidence_hash.slice(0, 10)}…</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {tab === "traba" && stalls && (
        <section className="mt-10">
          <p className="text-[13px] text-mute">
            SLA flyer 7 días / FAQ 10 días. Pagados en 7 días: {stalls.sla.within_7} de {stalls.sla.paid}.
          </p>
          <ul className="mt-6 divide-y divide-line">
            {stalls.stages.map((s: any) => (
              <li key={s.stage} className="grid grid-cols-[10rem_1fr_6rem] items-center gap-4 py-3 text-[14px]">
                <span>{s.stage || "—"}</span>
                <span className="h-1 bg-ink" style={{ width: `${Math.min(100, s.n / 80)}%` }} />
                <span className="text-right">{s.n}</span>
              </li>
            ))}
          </ul>
          <h3 className="mt-10 text-[13px] uppercase tracking-[0.14em] text-mute">Por qué rebota</h3>
          <ul className="mt-4 text-[14px]">
            {stalls.reasons.map((r: any) => (
              <li key={r.reason} className="flex justify-between border-b border-line py-2">
                <span>{r.reason}</span>
                <span>{r.n}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {tab === "bajas" && churn && (
        <section className="mt-10">
          <p className="text-[13px] text-mute">{churn.holdout}</p>
          <p className="mt-2 text-[13px] text-mute">{churn.note}</p>
          <ul className="mt-6 divide-y divide-line text-[14px]">
            {churn.by_plan.map((p: any) => (
              <li key={p.plan} className="grid grid-cols-5 py-2">
                <span>{p.plan}</span>
                <span>{p.n} socios</span>
                <span>{p.bajas} bajas</span>
                <span>riesgo {pct(p.risk)}</span>
                <span>{p.por_reintegro} por reintegro</span>
              </li>
            ))}
          </ul>
          <h3 className="mt-10 text-[13px] uppercase tracking-[0.14em] text-mute">En riesgo · sin dato de salud</h3>
          <ul className="mt-3 text-[13px]">
            {churn.at_risk.slice(0, 12).map((m: any) => (
              <li key={m.socio_nro} className="flex justify-between border-b border-line py-1.5">
                <span>{m.nombre} {m.apellido} · {m.plan} · {m.zona}</span>
                <span>{pct(m.churn_risk)} {m.holdout ? "holdout" : ""}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {tab === "mercado" && mercado && (
        <section className="mt-10">
          <p className="text-[13px] text-mute">{mercado.note}</p>
          <div className="mt-6 grid gap-8 md:grid-cols-2">
            <div>
              <h3 className="text-[13px] uppercase tracking-[0.14em] text-mute">Erosión de topes</h3>
              {mercado.caps.map((c: any) => (
                <div key={c.plan} className="mt-3 border-b border-line py-2 text-[14px]">
                  <div className="flex justify-between">
                    <span>{c.plan}</span>
                    <span>cubre {pct(c.cobertura_pct)}</span>
                  </div>
                  <div className="text-[12px] text-mute">
                    Tope {ars(c.tope_consulta)} · mercado {ars(c.mercado_mediana)} · Galeno 550 {ars(c.galeno_550)}
                  </div>
                </div>
              ))}
              <div className="mt-6">
                <label className="text-[13px]">Simular tope Global
                  <input type="number" className="ml-3 border px-2 py-1" value={tope} onChange={(e) => setTope(Number(e.target.value))} />
                </label>
                <button
                  className="ml-3 border px-3 py-1 text-[13px]"
                  onClick={async () => setSim(await post("/api/mercado/simular-tope", { plan: "GLOBAL", tope }))}
                >
                  Simular
                </button>
                {sim && (
                  <p className="mt-2 text-[13px] text-mute">
                    Cobertura {pct(sim.coverage_now)} → {pct(sim.coverage_new)} · extra {ars(sim.extra_spend_sample)} sobre la muestra.
                  </p>
                )}
              </div>
            </div>
            <div>
              <h3 className="text-[13px] uppercase tracking-[0.14em] text-mute">A reclutar</h3>
              <ul className="mt-3 text-[13px]">
                {mercado.recruit.slice(0, 10).map((d: any) => (
                  <li key={d.id} className="border-b border-line py-2">
                    <div>{d.nombre} · {d.especialidad} · {d.zona}</div>
                    <div className="text-mute">{d.visits} visitas · {d.why}</div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}
    </main>
  );
}
