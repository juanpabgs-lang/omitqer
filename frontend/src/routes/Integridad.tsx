import { useEffect, useState } from "react";
import { ars } from "../lib/format";
import { get, post } from "../lib/api";

export function Integridad() {
  const [liqs, setLiqs] = useState<any[]>([]);
  const [detail, setDetail] = useState<any>(null);
  const [refunds, setRefunds] = useState<any[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    get<any[]>("/api/integridad/liquidaciones").then(setLiqs);
    get<any[]>("/api/integridad/reintegros").then(setRefunds);
  }, []);

  async function openLiq(id: number) {
    const d = await get(`/api/integridad/liquidaciones/${id}`);
    setDetail(d);
  }

  async function confirm(id: number) {
    const r = await post<any>(`/api/integridad/debitos/${id}/confirmar`, { by: "Sara Leibovich" });
    setMsg(`Débito confirmado · ${ars(r.ars)} · ${r.hash.slice(0, 12)}…`);
    if (detail) openLiq(detail.liquidacion.id);
    setLiqs(await get("/api/integridad/liquidaciones"));
  }

  return (
    <main className="mx-auto max-w-[1440px] px-[clamp(16px,5.4vw,104px)] py-16">
      <p className="text-[12px] uppercase tracking-[0.16em] text-mute">Integridad de pago</p>
      <h1 className="mt-3 max-w-3xl text-[clamp(32px,4vw,52px)] tracking-[-0.03em]">
        El reintegro es el 1%. El gasto de cartilla es el resto.
      </h1>
      <p className="mt-4 max-w-2xl text-[16px] text-mute">
        El motor lee cada renglón contra el convenio escrito como código. Propone el débito.
        Una persona confirma. Precisión y recall se miden contra anomalías que nosotros plantamos.
      </p>

      <div className="mt-12 grid gap-10 lg:grid-cols-2">
        <section>
          <h2 className="text-[13px] uppercase tracking-[0.14em] text-mute">Liquidaciones sintéticas · sep 2026</h2>
          <ul className="mt-4 divide-y divide-line">
            {liqs.map((l) => (
              <li key={l.id} className="flex cursor-pointer justify-between py-3" onClick={() => openLiq(l.id)}>
                <div>
                  <div>{l.provider_name}</div>
                  <div className="text-[12px] text-mute">{l.debitos_n} débitos propuestos</div>
                </div>
                <div className="text-right text-[13px]">
                  <div>{ars(l.total)}</div>
                  <div className="text-mute">confirmado {ars(l.confirmado_ars)}</div>
                </div>
              </li>
            ))}
          </ul>
        </section>
        <section>
          {detail ? (
            <div>
              <div className="flex justify-between">
                <h2 className="text-[18px]">{detail.liquidacion.provider_name}</h2>
                <div className="text-[13px] text-mute">
                  P {detail.precision} · R {detail.recall} · plantadas {detail.planted} · pescadas {detail.caught}
                </div>
              </div>
              <ul className="mt-4 max-h-[480px] overflow-auto divide-y divide-line text-[13px]">
                {detail.proposed.map((p: any) => (
                  <li key={p.line_id} className="flex items-start justify-between gap-4 py-2">
                    <div>
                      <div>{p.descripcion} · {p.codigo}</div>
                      <div className="text-mute">{p.reasons.join(" · ")} {p.planted ? `· semilla ${p.planted}` : ""}</div>
                    </div>
                    <button className="border border-line px-2 py-1" onClick={() => confirm(p.debit_id)}>
                      Confirmar {ars(p.importe)}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-mute">Elegí una liquidación.</p>
          )}
          {msg && <p className="mt-4 text-[13px]">{msg}</p>}
        </section>
      </div>

      <section className="mt-16">
        <h2 className="text-[13px] uppercase tracking-[0.14em] text-mute">Fugas en reintegros</h2>
        <ul className="mt-4 divide-y divide-line text-[13px]">
          {refunds.slice(0, 16).map((r, i) => (
            <li key={i} className="py-2">
              <span className="text-mute">{r.kind}</span> · {r.detail}
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
