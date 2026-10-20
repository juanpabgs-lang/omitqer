import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ars } from "../lib/format";
import { get } from "../lib/api";

export function Operaciones() {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<any[]>([]);

  useEffect(() => {
    get<any[]>(`/api/claims${q ? `?queue=${q}` : ""}`).then(setRows);
  }, [q]);

  return (
    <main className="mx-auto max-w-[1440px] px-[clamp(16px,5.4vw,104px)] py-16">
      <p className="text-[12px] uppercase tracking-[0.16em] text-mute">Mesa de operaciones</p>
      <h1 className="mt-3 text-[clamp(32px,4vw,48px)] tracking-[-0.03em]">El expediente llega armado.</h1>
      <div className="mt-8 flex gap-4 text-[13px]">
        {[
          ["", "todos"],
          ["revision", "revisión"],
          ["falta", "falta documentación"],
          ["via_rapida", "vía rápida"],
          ["pagados", "pagados"],
        ].map(([k, l]) => (
          <button key={k} onClick={() => setQ(k)} className={q === k ? "underline decoration-mint underline-offset-4" : "text-mute"}>
            {l}
          </button>
        ))}
      </div>
      <table className="mt-8 w-full text-left text-[13px]">
        <thead className="text-mute">
          <tr>
            <th className="py-2 font-normal">ID</th>
            <th className="font-normal">Socio</th>
            <th className="font-normal">Plan</th>
            <th className="font-normal">Ruta</th>
            <th className="font-normal">Estado</th>
            <th className="font-normal text-right">Estimado</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-line">
              <td className="py-2">
                <Link className="underline" to={`/expediente/${r.id}`}>{r.public_id}</Link>
              </td>
              <td>{r.nombre} {r.apellido}</td>
              <td>{r.plan}</td>
              <td>{r.route}</td>
              <td>{r.status}</td>
              <td className="text-right">{ars(r.estimado)}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td className="py-8 text-mute" colSpan={6}>
                No hay vivos en esta cola. Enviá un reintegro desde /socio.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </main>
  );
}
