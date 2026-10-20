import { useEffect, useState } from "react";
import { CheckRow } from "../components/CheckRow";
import { PhoneFrame } from "../components/PhoneFrame";
import { ars } from "../lib/format";
import { get, post } from "../lib/api";

type Sample = { key: string; title: string; subtitle: string; expected_route: string };

export function Socio() {
  const [samples, setSamples] = useState<Sample[]>([]);
  const [sel, setSel] = useState<string>("consulta_limpia");
  const [bundle, setBundle] = useState<any>(null);
  const [claim, setClaim] = useState<any>(null);
  const [cuir, setCuir] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<"foto" | "antes">("foto");
  const [presupuesto, setPresupuesto] = useState<any>(null);

  useEffect(() => {
    get<Sample[]>("/api/samples").then(setSamples).catch(() => setSamples([]));
  }, []);

  async function run(overrides?: Record<string, unknown>) {
    setBusy(true);
    setErr(null);
    setClaim(null);
    try {
      const b = await post("/api/precheck", { sample_key: sel, overrides });
      setBundle(b);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function enviar() {
    setBusy(true);
    try {
      const r = await post("/api/claims", { sample_key: sel, overrides: cuir ? { cuir } : {} });
      setClaim(r);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function verPresupuesto() {
    const r = await get("/api/socio/presupuesto?especialidad=Cardiolog%C3%ADa&zona=CABA&plan=GLOBAL");
    setPresupuesto(r);
  }

  const ev = bundle?.evaluation;

  return (
    <main className="bg-[#0b1020] py-16 text-white">
      <div className="mx-auto grid max-w-[1440px] gap-16 px-[clamp(16px,5.4vw,104px)] lg:grid-cols-12">
        <div className="lg:col-span-5">
          <p className="text-[12px] uppercase tracking-[0.16em] text-white/40">App del socio · voseo</p>
          <h1 className="mt-4 font-omint text-[clamp(32px,4vw,48px)] leading-tight tracking-[-0.03em]">
            Fotografiá la factura. Sabé cuánto vuelve. Hoy.
          </h1>
          <p className="mt-4 text-[15px] text-white/60">
            La palabra “rechazado” no existe. Si falta algo, te lo decimos antes de enviar.
            Si está limpio, el dinero sale en minutos.
          </p>
          <div className="mt-8 space-y-2">
            {samples.map((s) => (
              <button
                key={s.key}
                onClick={() => {
                  setSel(s.key);
                  setBundle(null);
                  setClaim(null);
                }}
                className={`block w-full border px-3 py-2 text-left text-[13px] ${
                  sel === s.key ? "border-[#aa9756] bg-white/5" : "border-white/10"
                }`}
              >
                <div>{s.title}</div>
                <div className="text-white/40">{s.subtitle}</div>
              </button>
            ))}
          </div>
          <div className="mt-6 flex gap-3">
            <button onClick={() => run(cuir ? { cuir } : undefined)} className="bg-[#aa9756] px-4 py-2 text-[13px] text-black">
              {busy ? "Leyendo…" : "Leer documento"}
            </button>
            <button onClick={() => setTab(tab === "foto" ? "antes" : "foto")} className="border border-white/20 px-4 py-2 text-[13px]">
              {tab === "foto" ? "Antes de ir" : "Volver a la foto"}
            </button>
          </div>
          {err && <p className="mt-3 text-[13px] text-red-300">{err}</p>}
        </div>

        <div className="lg:col-span-7">
          <PhoneFrame>
            <div className="omint bg-white px-5 py-4">
              <div className="flex items-center justify-between">
                <span className="text-[11px] tracking-[0.2em] text-[#002583]">OMINT</span>
                <span className="text-[11px] text-[#888]">Reintegros</span>
              </div>
              {tab === "antes" ? (
                <div className="mt-6">
                  <h2 className="text-[22px] text-[#002583]">Antes de ir al consultorio</h2>
                  <p className="mt-2 text-[13px] text-[#555]">Cardiología · CABA · plan Global</p>
                  <button onClick={verPresupuesto} className="mt-4 bg-[#002583] px-3 py-2 text-[13px] text-white">
                    Estimar mi gasto
                  </button>
                  {presupuesto && (
                    <div className="mt-4 text-[14px]">
                      <p>OMINT reconoce {ars(presupuesto.omint_paga)}</p>
                      <p className="mt-1">Vas a pagar {ars(presupuesto.socio_paga)}</p>
                      <p className="mt-2 text-[12px] text-[#666]">
                        {presupuesto.directo ? "Tu médico está en OMINT Directo." : "Rango de mercado, no un médico nombrado."}
                      </p>
                    </div>
                  )}
                </div>
              ) : !ev ? (
                <div className="mt-16 text-center text-[14px] text-[#666]">
                  Elegí un comprobante sintético a la izquierda.
                </div>
              ) : (
                <div className="mt-4">
                  <p className="text-[12px] text-[#888]">{bundle.member.nombre} · {bundle.member.plan}</p>
                  <p className="mt-2 text-[13px] text-[#002583]">{ev.summary}</p>
                  <div className="mt-4">
                    <div className="text-[11px] uppercase tracking-[0.14em] text-[#888]">Te devolvemos</div>
                    <div className="text-[34px] text-[#002583]">{ars(ev.estimate.recognized)}</div>
                    <div className="text-[12px] text-[#666]">
                      Facturaste {ars(ev.estimate.billed)} · tope {ars(ev.estimate.tope)} · a tu cargo {ars(ev.estimate.out_of_pocket)}
                    </div>
                    {ev.estimate.sesiones_restantes != null && (
                      <div className="text-[12px] text-[#666]">Sesiones restantes este año: {ev.estimate.sesiones_restantes}</div>
                    )}
                    <div className="mt-2 text-[12px] text-[#666]">
                      {ev.route === "via_rapida" ? "Acreditación en minutos (sandbox)." : `Estimado ${ev.pay_on}`}
                    </div>
                  </div>
                  {ev.missing?.length > 0 && (
                    <div className="mt-4 border border-[#aa9756] p-3 text-[13px]">
                      Te falta {ev.missing.length} {ev.missing.length === 1 ? "cosa" : "cosas"}: {ev.missing.join(", ")}
                      {ev.missing.includes("orden_medica") && (
                        <div className="mt-2">
                          <input
                            value={cuir}
                            onChange={(e) => setCuir(e.target.value)}
                            placeholder="CUIR-AR-2026-00018422-07"
                            className="w-full border px-2 py-1 text-[12px]"
                          />
                          <button
                            className="mt-2 text-[12px] underline"
                            onClick={() => run({ cuir: cuir || "CUIR-AR-2026-00018422-07" })}
                          >
                            Adjuntar orden digital
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                  <div className="mt-4 max-h-48 overflow-auto">
                    {ev.checks.slice(0, 8).map((c: any) => (
                      <CheckRow key={c.name} name={c.name} ok={c.ok} result={c.result} source={c.source} />
                    ))}
                  </div>
                  {ev.conflicts?.length > 0 && (
                    <p className="mt-3 text-[11px] text-[#666]">{ev.conflicts[0]}</p>
                  )}
                  {ev.route !== "falta_doc" && !claim && (
                    <button onClick={enviar} className="mt-4 w-full bg-[#002583] py-2.5 text-[13px] text-white">
                      Enviar reintegro
                    </button>
                  )}
                  {claim && (
                    <div className="mt-4 border border-[#00fe99] bg-[#f3fff9] p-3 text-[13px]">
                      <div className="text-[#002583]">{claim.claim.public_id}</div>
                      <div>Estado: {claim.claim.status}</div>
                      {claim.payment && <div>Acreditado {ars(claim.payment.amount)} · {claim.payment.tx_ref}</div>}
                    </div>
                  )}
                </div>
              )}
            </div>
          </PhoneFrame>
        </div>
      </div>
    </main>
  );
}
