import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { get } from "../lib/api";

export function Verificar() {
  const { hash } = useParams();
  const [d, setD] = useState<any>(null);

  useEffect(() => {
    if (hash) get(`/api/verificar/${hash}`).then(setD);
    else get("/api/ledger/valor").then((v: any) => setD({ chain: v.chain, found: v.chain.ok }));
  }, [hash]);

  if (!d) return <main className="p-16">Verificando…</main>;
  return (
    <main className="mx-auto max-w-[880px] px-[clamp(16px,5.4vw,104px)] py-16">
      <p className="text-[12px] uppercase tracking-[0.16em] text-mute">Verificación pública</p>
      <h1 className="mt-3 text-[36px] tracking-[-0.03em]">
        {d.chain?.ok ? "La cadena está íntegra." : "La cadena no cierra."}
      </h1>
      <p className="mt-3 text-[14px] text-mute">
        {d.found ? "El hash existe en el ledger." : "Hash no encontrado. Se muestra el estado de la cadena."}
      </p>
      {d.event && (
        <pre className="mt-6 overflow-auto border border-line bg-panel p-4 text-[12px]">{JSON.stringify(d.event, null, 2)}</pre>
      )}
      {d.public_key && <pre className="mt-4 text-[11px] text-mute">{d.public_key}</pre>}
    </main>
  );
}
