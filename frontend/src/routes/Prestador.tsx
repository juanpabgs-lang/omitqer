import { useEffect, useState } from "react";
import { PhoneFrame } from "../components/PhoneFrame";
import { ars } from "../lib/format";
import { get, post } from "../lib/api";

export function Prestador() {
  const [docs, setDocs] = useState<any[]>([]);
  const [sel, setSel] = useState<any>(null);
  const [cuit, setCuit] = useState("");
  const [mat, setMat] = useState("");
  const [cbu, setCbu] = useState("0170099220000034567891");
  const [socio, setSocio] = useState("");
  const [visit, setVisit] = useState<any>(null);
  const [att, setAtt] = useState<any>(null);
  const [payouts, setPayouts] = useState<any[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    get<any[]>("/api/directo/doctors").then((d) => {
      setDocs(d);
      const first = d.find((x) => !x.en_directo && x.refeps_estado === "HABILITADO") || d[0];
      setSel(first);
      setCuit(first?.cuit || "");
      setMat(first?.matricula || "");
    });
    get<any[]>("/api/samples").then((s) => {
      /* socio nro from a known sample member via claims not needed */
    });
  }, []);

  useEffect(() => {
    get<any[]>("/api/claims?limit=5").catch(() => []);
    get<any>("/api/direccion/churn").then((c) => {
      const n = "400001";
      setSocio(n);
    }).catch(() => setSocio("400001"));
  }, []);

  async function alta() {
    const r = await post<any>("/api/directo/onboard", { cuit, matricula: mat, cbu });
    setMsg(r.ok ? `Alta ${r.doctor.nombre}` : r.reason);
    const d = await get<any[]>("/api/directo/doctors");
    setDocs(d);
  }

  async function atender() {
    if (!sel) return;
    const r = await post<any>("/api/directo/atender", { professional_id: sel.id, socio_nro: socio });
    setVisit(r);
    setMsg(r.pending || r.reason);
  }

  async function confirmar() {
    if (!visit?.attestation_id) return;
    const r = await post<any>("/api/directo/attest", { attestation_id: visit.attestation_id, socio_nro: socio });
    setAtt(r);
    setMsg(r.ok ? "El socio confirmó en su app. No hubo login compartido." : r.reason);
  }

  return (
    <main className="bg-[#0b1020] py-16 text-white">
      <div className="mx-auto grid max-w-[1440px] gap-16 px-[clamp(16px,5.4vw,104px)] lg:grid-cols-12">
        <div className="lg:col-span-5">
          <p className="text-[12px] uppercase tracking-[0.16em] text-white/40">OMINT Directo</p>
          <h1 className="mt-4 text-[clamp(32px,4vw,48px)] tracking-[-0.03em]">
            El médico cobra en 24 horas. El socio solo paga la diferencia.
          </h1>
          <p className="mt-4 text-[15px] text-white/60">
            Alta en tres minutos: CUIT contra padrón ARCA, matrícula contra REFEPS, CBU.
            El socio confirma en su propia app — la salvaguarda contra el fraude brasileño
            de “reembolso assistido”.
          </p>
          <div className="mt-8 space-y-3 text-[13px]">
            <label className="block">CUIT
              <input value={cuit} onChange={(e) => setCuit(e.target.value)} className="mt-1 w-full border border-white/20 bg-transparent px-2 py-1" />
            </label>
            <label className="block">Matrícula
              <input value={mat} onChange={(e) => setMat(e.target.value)} className="mt-1 w-full border border-white/20 bg-transparent px-2 py-1" />
            </label>
            <label className="block">CBU
              <input value={cbu} onChange={(e) => setCbu(e.target.value)} className="mt-1 w-full border border-white/20 bg-transparent px-2 py-1" />
            </label>
            <button onClick={alta} className="bg-[#aa9756] px-4 py-2 text-black">Dar de alta</button>
            <label className="block">N° de socio
              <input value={socio} onChange={(e) => setSocio(e.target.value)} className="mt-1 w-full border border-white/20 bg-transparent px-2 py-1" />
            </label>
            <div className="flex gap-2">
              <button onClick={atender} className="border border-white/30 px-4 py-2">Atender socio</button>
              <button onClick={confirmar} className="border border-white/30 px-4 py-2">Confirmar en app del socio</button>
            </div>
            {msg && <p className="text-[#aa9756]">{msg}</p>}
          </div>
        </div>
        <div className="lg:col-span-7">
          <PhoneFrame>
            <div className="omint p-5">
              <div className="text-[11px] tracking-[0.2em] text-[#002583]">OMINT DIRECTO</div>
              <h2 className="mt-3 text-[22px]">Consultorio</h2>
              <p className="mt-2 text-[13px] text-[#555]">
                {sel ? `${sel.nombre} · ${sel.especialidad} · ${sel.en_directo ? "adherido" : "fuera"}` : "—"}
              </p>
              {visit?.ok && (
                <div className="mt-4 border p-3 text-[13px]">
                  Visita {visit.attestation_id}<br />
                  {visit.member.nombre} · {visit.member.plan}
                  <div className="mt-2 text-[12px] text-[#666]">{visit.pending}</div>
                </div>
              )}
              {att?.ok && (
                <div className="mt-4 bg-[#002583] p-3 text-[13px] text-white">
                  Confirmado {att.confirmed_at}
                  <div className="text-[11px] opacity-70">hash {att.hash?.slice(0, 16)}…</div>
                </div>
              )}
              <div className="mt-6 text-[12px] uppercase tracking-[0.14em] text-[#888]">Red</div>
              <ul className="mt-2 max-h-64 overflow-auto text-[12px]">
                {docs.filter((d) => d.en_directo).slice(0, 12).map((d) => (
                  <li key={d.id} className="border-b py-1.5">{d.nombre} · {d.especialidad} · {ars(d.precio_base)}</li>
                ))}
              </ul>
            </div>
          </PhoneFrame>
        </div>
      </div>
    </main>
  );
}
