import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CheckRow } from "../components/CheckRow";
import { Timeline } from "../components/Timeline";
import { ars } from "../lib/format";
import { get, post } from "../lib/api";

export function Expediente() {
  const { id } = useParams();
  const [d, setD] = useState<any>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [reason, setReason] = useState("Cartilla 4021 req. (b): prestación fuera de cobertura.");
  const [second, setSecond] = useState("Marcos Villa Larroudet");

  async function load() {
    setD(await get(`/api/claims/${id}`));
  }
  useEffect(() => {
    load();
  }, [id]);

  async function act(action: string) {
    try {
      const r = await post<any>(`/api/claims/${id}/actions`, {
        action,
        by: "Mesa Norte",
        reason,
        second: action === "negar" ? second : undefined,
      });
      setMsg(JSON.stringify(r));
      await load();
    } catch (e: any) {
      setMsg(e.message);
    }
  }

  if (!d) return <main className="p-16">Cargando…</main>;
  const c = d.claim;

  return (
    <main className="mx-auto max-w-[1440px] px-[clamp(16px,5.4vw,104px)] py-16">
      <p className="text-[12px] uppercase tracking-[0.16em] text-mute">Expediente {c.public_id}</p>
      <h1 className="mt-3 text-[32px] tracking-[-0.03em]">{d.member.nombre} · {d.member.plan}</h1>
      <p className="mt-2 text-[15px] text-mute">
        {c.tipo} · {ars(c.importe)} facturado · {ars(c.estimado)} reconocido · {c.route} · {c.status}
      </p>
      <div className="mt-8 grid gap-12 lg:grid-cols-2">
        <section>
          <h2 className="text-[13px] uppercase tracking-[0.14em] text-mute">Verificaciones</h2>
          {d.checks.map((chk: any) => (
            <CheckRow key={chk.id} name={chk.name} ok={!!chk.ok} result={chk.result} source={chk.source} />
          ))}
          <p className="mt-4 text-[12px] text-mute">El diagnóstico está oculto fuera de auditoría médica.</p>
        </section>
        <section>
          <h2 className="text-[13px] uppercase tracking-[0.14em] text-mute">Línea de tiempo</h2>
          <Timeline items={d.timeline} />
          <div className="mt-8 flex flex-wrap gap-2 text-[13px]">
            <button className="bg-ink px-3 py-1.5 text-paper" onClick={() => act("aprobar")}>Aprobar y pagar</button>
            <button className="border px-3 py-1.5" onClick={() => act("pedir_documentos")}>Pedir documentos</button>
            <button className="border px-3 py-1.5" onClick={() => act("auditoria_medica")}>Auditoría médica</button>
          </div>
          <div className="mt-6 border border-warn/40 p-3 text-[13px]">
            <div>Negativa humana — exige motivo citado y segunda firma</div>
            <input className="mt-2 w-full border px-2 py-1" value={reason} onChange={(e) => setReason(e.target.value)} />
            <input className="mt-2 w-full border px-2 py-1" value={second} onChange={(e) => setSecond(e.target.value)} />
            <button className="mt-2 border border-warn px-3 py-1" onClick={() => act("negar")}>Negar</button>
          </div>
          <div className="mt-6 flex gap-4 text-[13px]">
            <Link className="underline" to={`/verificar/${""}`}>Ver pack</Link>
            <a className="underline" href={`/api/expediente/${id}/evidencia.pdf`}>PDF</a>
            <a className="underline" href={`/api/expediente/${id}/evidencia`}>JSON</a>
          </div>
          {msg && <pre className="mt-4 whitespace-pre-wrap text-[12px] text-mute">{msg}</pre>}
        </section>
      </div>
    </main>
  );
}
