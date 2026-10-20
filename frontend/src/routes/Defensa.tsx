import { useEffect, useState } from "react";
import { get, post } from "../lib/api";

export function Defensa() {
  const [rows, setRows] = useState<any[]>([]);
  const [rules, setRules] = useState<any>(null);
  const [letter, setLetter] = useState<string | null>(null);
  const [vault, setVault] = useState<any[] | null>(null);

  useEffect(() => {
    get<any[]>("/api/defensa/denuncias").then(setRows);
    get("/api/reglas").then(setRules);
  }, []);

  async function responder(id: number) {
    const r = await post<any>(`/api/defensa/${id}/descargo`, {});
    setLetter(r.letter);
    setRows(await get("/api/defensa/denuncias"));
  }

  async function contrato(memberId: number) {
    setVault(await get(`/api/contratos/${memberId}`));
  }

  return (
    <main className="mx-auto max-w-[1440px] px-[clamp(16px,5.4vw,104px)] py-16">
      <p className="text-[12px] uppercase tracking-[0.16em] text-mute">Res. SSSalud 951/2026</p>
      <h1 className="mt-3 max-w-3xl text-[clamp(32px,4vw,52px)] tracking-[-0.03em]">
        Cinco días hábiles. El silencio cuenta como culpa.
      </h1>
      <p className="mt-4 max-w-2xl text-[16px] text-mute">
        Art. 2: presunción iuris tantum. Art. 4: acreditar fehaciente; pagar después de la INTIMA
        es regularización extemporánea. El contrato se recupera por hash — el eco de D.B./L.B.
      </p>

      <section className="mt-12">
        <h2 className="text-[13px] uppercase tracking-[0.14em] text-mute">Bandeja</h2>
        <ul className="mt-4 divide-y divide-line text-[13px]">
          {rows.map((d) => (
            <li key={d.id} className="grid grid-cols-[8rem_1fr_auto] items-center gap-4 py-3">
              <span className={d.dias_restantes < 2 ? "text-warn" : ""}>
                {d.dias_restantes} d hábiles
              </span>
              <div>
                <div>{d.public_id} · {d.tipo}</div>
                <div className="text-mute">{d.asunto} · {d.nombre} {d.apellido}</div>
              </div>
              <div className="flex gap-2">
                <button className="border px-2 py-1" onClick={() => contrato(d.member_id)}>Contrato</button>
                <button className="bg-ink px-2 py-1 text-paper" onClick={() => responder(d.id)}>Descargo</button>
              </div>
            </li>
          ))}
        </ul>
        {letter && <pre className="mt-6 max-w-3xl whitespace-pre-wrap border border-line bg-panel p-4 text-[13px]">{letter}</pre>}
        {vault && (
          <ul className="mt-4 text-[13px]">
            {vault.map((c) => (
              <li key={c.id}>{c.version} · {c.signed_at} · {c.sha256}</li>
            ))}
          </ul>
        )}
      </section>

      {rules && (
        <section className="mt-16">
          <h2 className="text-[13px] uppercase tracking-[0.14em] text-mute">Contradicciones propias de OMINT</h2>
          <ul className="mt-4 space-y-6">
            {rules.conflicts.map((c: any) => (
              <li key={c.a} className="border-t border-line pt-4">
                <div className="text-[16px]">{c.title_a} vs {c.title_b}</div>
                <p className="mt-2 text-[13px] text-mute">“{c.quote_a}”</p>
                <p className="text-[13px] text-mute">“{c.quote_b}”</p>
                <p className="mt-2 text-[13px]">{c.resolution}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
