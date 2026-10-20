import { useEffect, useState } from "react";
import { get } from "../lib/api";

export function Sap() {
  const [rows, setRows] = useState<any[]>([]);

  useEffect(() => {
    get<any[]>("/api/sap/outbox").then(setRows);
  }, []);

  return (
    <main className="mx-auto max-w-[1440px] px-[clamp(16px,5.4vw,104px)] py-16">
      <p className="text-[12px] uppercase tracking-[0.16em] text-mute">SAP S/4HANA Public Cloud</p>
      <h1 className="mt-3 max-w-3xl text-[clamp(32px,4vw,52px)] tracking-[-0.03em]">
        Clean core. APIs liberadas. Nada de Z.
      </h1>
      <p className="mt-4 max-w-2xl text-[16px] text-mute">
        GROW with SAP, anunciado en SAP NOW Argentina 2026. Los reintegros salen por
        API_SUPPLIERINVOICE_PROCESS_SRV (SAP_COM_0057) o Journal Entry – Post (SAP_COM_0002).
        Antes del go-live, el mismo payload se exporta al sistema actual.
      </p>

      <section className="mt-12 grid gap-10 md:grid-cols-2">
        <div>
          <h2 className="text-[13px] uppercase tracking-[0.14em] text-mute">Principios</h2>
          <ul className="mt-4 list-disc space-y-2 pl-5 text-[14px]">
            <li>Solo APIs released. Cero extensiones Z en el ERP.</li>
            <li>El motor vive al lado, no adentro.</li>
            <li>La evidencia no viaja a US-hosted LLMs. Ley 25.326.</li>
            <li>Pago sandbox: transferencia instantánea; recupero por próxima factura.</li>
          </ul>
        </div>
        <div>
          <h2 className="text-[13px] uppercase tracking-[0.14em] text-mute">Camino a producción</h2>
          <ul className="mt-4 list-disc space-y-2 pl-5 text-[14px] text-mute">
            <li>Certificado WSAA y WSCDC en homologación ARCA, CUIT OMINT.</li>
            <li>Convenio SISA REFEPS y repositorio ReNaPDiS.</li>
            <li>BTP o OData directo.</li>
            <li>Sellos anclados en Blockchain Federal Argentina.</li>
            <li>Piloto: solo consultas y sesiones.</li>
          </ul>
        </div>
      </section>

      <section className="mt-14">
        <h2 className="text-[13px] uppercase tracking-[0.14em] text-mute">Outbox</h2>
        {rows.length === 0 && <p className="mt-4 text-mute">Todavía no hay posteos. Enviá un reintegro por vía rápida.</p>}
        <ul className="mt-4 space-y-4">
          {rows.map((r) => (
            <li key={r.id} className="border border-line p-4">
              <div className="text-[13px]">{r.api} · {r.comm_scenario} · {r.status}</div>
              <pre className="mt-2 max-h-48 overflow-auto text-[11px] text-mute">{JSON.stringify(r.payload, null, 2)}</pre>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
