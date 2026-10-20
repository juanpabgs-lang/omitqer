import { useEffect, useState } from "react";
import { compact, usd } from "../lib/format";
import { get, post } from "../lib/api";

export function Caso() {
  const [data, setData] = useState<any>(null);
  const [inputs, setInputs] = useState<Record<string, number>>({});

  useEffect(() => {
    get<any>("/api/roi").then((d) => {
      setData(d);
      const init: Record<string, number> = {};
      for (const i of d.inputs) init[i.key] = i.value;
      setInputs(init);
    });
  }, []);

  async function simular() {
    const d = await post<any>("/api/roi/simular", { inputs });
    setData({ ...data, ...d });
  }

  if (!data) return <main className="px-[clamp(16px,5.4vw,104px)] py-20">Cargando modelo…</main>;

  return (
    <main className="mx-auto max-w-[1440px] px-[clamp(16px,5.4vw,104px)] py-16">
      <p className="text-[12px] uppercase tracking-[0.16em] text-mute">Caso de negocio</p>
      <h1 className="mt-3 max-w-3xl text-[clamp(32px,4vw,52px)] tracking-[-0.03em]">
        {compact(data.run_rate_ars)} al año. {usd(data.run_rate_usd)}. Cada peso tiene dueño.
      </h1>
      <p className="mt-4 max-w-2xl text-[16px] text-mute">{data.disclaimer}</p>

      <div className="mt-10 grid gap-8 md:grid-cols-3">
        <Card k="Run-rate" v={compact(data.run_rate_ars)} s={`P10 ${compact(data.monte_carlo.p10)} · P90 ${compact(data.monte_carlo.p90)}`} />
        <Card k="Año 1 neto de build" v={compact(data.year1_ars)} s={`Solución ${compact(data.solution_ars)}`} />
        <Card k="Payback" v={`${data.payback_months?.toFixed(1)} meses`} s={`${data.fte_freed.toFixed(1)} FTE reasignados · ${data.kept_members.toFixed(0)} socios`} />
      </div>

      <section className="mt-14">
        <h2 className="text-[13px] uppercase tracking-[0.14em] text-mute">Palancas</h2>
        <ul className="mt-4 divide-y divide-line">
          {data.levers.map((l: any) => (
            <li key={l.id} className="grid grid-cols-[1fr_auto] gap-6 py-4">
              <div>
                <div className="text-[17px]">{l.name}</div>
                <div className="text-[13px] text-mute">{l.formula}</div>
                <div className="text-[13px] text-mute">{l.note}</div>
              </div>
              <div className="text-[20px]">{compact(l.ars)}</div>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-14">
        <h2 className="text-[13px] uppercase tracking-[0.14em] text-mute">Supuestos editables</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {data.inputs.map((i: any) => (
            <label key={i.key} className="grid grid-cols-[1fr_8rem] items-center gap-3 border-b border-line py-2 text-[13px]">
              <span>
                {i.label}
                <span className="ml-2 text-[11px] uppercase text-mute">{i.provenance}</span>
                <span className="block text-[11px] text-mute">{i.source}</span>
              </span>
              <input
                className="border border-line bg-panel px-2 py-1 text-right"
                type="number"
                step="any"
                value={inputs[i.key] ?? i.value}
                onChange={(e) => setInputs({ ...inputs, [i.key]: Number(e.target.value) })}
              />
            </label>
          ))}
        </div>
        <button onClick={simular} className="mt-6 bg-ink px-4 py-2 text-[13px] text-paper">
          Recalcular
        </button>
      </section>

      <section className="mt-14 grid gap-10 md:grid-cols-2">
        <div>
          <h2 className="text-[13px] uppercase tracking-[0.14em] text-mute">Rampa 12 meses</h2>
          <ul className="mt-3 text-[13px]">
            {data.ramp.filter((_: any, i: number) => [0, 2, 5, 11].includes(i)).map((m: any) => (
              <li key={m.month} className="flex justify-between border-b border-line py-2">
                <span>Mes {m.month} · {Math.round(m.frac * 100)}%</span>
                <span>{compact(m.ars * 12)} anualizado</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="text-[13px] uppercase tracking-[0.14em] text-mute">Volante</h2>
          <ul className="mt-3 text-[13px]">
            {data.flywheel.map((f: any) => (
              <li key={f.month} className="flex justify-between border-b border-line py-2">
                <span>M{f.month}</span>
                <span>{f.doctors_directo} médicos · STP {(f.stp * 100).toFixed(0)}% · nacidos completos {(f.born_complete * 100).toFixed(0)}%</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="mt-16 border border-line bg-panel p-8">
        <p className="text-[12px] uppercase tracking-[0.14em] text-mute">Próximo paso</p>
        <h2 className="mt-2 text-[28px] tracking-[-0.03em]">Diagnóstico de fuga · tres semanas</h2>
        <p className="mt-3 max-w-2xl text-[15px] text-mute">
          Corremos el motor sobre un mes de reintegros y dos liquidaciones de prestadores,
          en la infraestructura de OMINT. La fuga medida llega antes de cualquier contrato de build.
        </p>
      </section>
    </main>
  );
}

function Card({ k, v, s }: { k: string; v: string; s: string }) {
  return (
    <div className="border-t border-ink pt-4">
      <div className="text-[12px] uppercase tracking-[0.14em] text-mute">{k}</div>
      <div className="mt-2 text-[26px]">{v}</div>
      <div className="mt-2 text-[13px] text-mute">{s}</div>
    </div>
  );
}
