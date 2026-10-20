import { useEffect, useState } from "react";
import { get, post } from "../lib/api";

export function Discapacidad() {
  const [rows, setRows] = useState<any[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    get<any[]>("/api/discapacidad/planillas").then(setRows);
  }, []);

  async function firmar(id: number) {
    const r = await post<any>(`/api/discapacidad/planillas/${id}/firmar`, { by: "Prestador sintético" });
    setMsg(`Firmada · ${r.hash.slice(0, 16)}…`);
    setRows(await get("/api/discapacidad/planillas"));
  }

  return (
    <main className="mx-auto max-w-[1440px] px-[clamp(16px,5.4vw,104px)] py-16">
      <p className="text-[12px] uppercase tracking-[0.16em] text-mute">Discapacidad</p>
      <h1 className="mt-3 max-w-3xl text-[clamp(32px,4vw,48px)] tracking-[-0.03em]">
        La planilla deja de ser un papel manuscrito.
      </h1>
      <p className="mt-4 max-w-2xl text-[16px] text-mute">
        INS-SER-DIS-004 pedía planillas a mano y notas del transportista. Acá el prestador
        firma digitalmente la asistencia. El CUD se verifica en sandbox. Nadie es denegado
        por un motor.
      </p>
      <ul className="mt-10 divide-y divide-line text-[14px]">
        {rows.map((r) => (
          <li key={r.id} className="flex items-center justify-between py-3">
            <div>
              <div>{r.nombre} {r.apellido} · {r.period}</div>
              <div className="text-[12px] text-mute">
                {r.provider} · días {r.days} · CUD {r.cud} {r.cud_ok ? "vigente" : ""}
                {r.signed_at ? ` · firmada ${r.signed_at}` : ""}
              </div>
            </div>
            <button className="border px-3 py-1" onClick={() => firmar(r.id)}>Firmar</button>
          </li>
        ))}
      </ul>
      {msg && <p className="mt-4 text-[13px]">{msg}</p>}
    </main>
  );
}
