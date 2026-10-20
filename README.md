# OMINT · Reintegro verificado

Demo en español (Argentina) para OMINT. El reintegro es la puerta. La ventaja es una red de médicos de sistema abierto que cobra en 24 h, un mapa de precios verificados, un ledger sellado para Res. SSSalud 951/2026 y la integridad de lo que factura la cartilla.

**Datos 100% sintéticos.** Ley 25.326. Ningún socio, profesional ni diagnóstico real.

## Cómo correrlo

```bash
./scripts/dev.sh
```

- UI: http://127.0.0.1:5178
- API: http://127.0.0.1:8018
- Symlink: `~/Norfront/demos/omint-reintegros`

```bash
PYTHONPATH=. python3 -m backend.app.seed   # mundo sintético
cd frontend && npm install && npm run dev
PYTHONPATH=. python3 -m uvicorn backend.app.main:app --port 8018
PYTHONPATH=. python3 -m pytest backend/tests -q
cd frontend && npx tsc --noEmit && npm run build
```

## Guion de demo (15 minutos)

1. **/** — Una frase. OSDE ya lee el QR. El foso es otra cosa. Teclas 1–6.
2. **`/socio`** — Factura limpia: monto, tope, pago en minutos. Después `kine_sin_orden`: “te falta 1 cosa”, se adjunta CUIR-AR-2026-00018422-07.
3. **`/prestador`** — Alta por CUIT + REFEPS + CBU. El socio confirma en *su* app (guarda contra reembolso assistido).
4. **`/integridad`** — Liquidación de Clínica del Sol. Precisión/recall contra semillas. Confirmar un débito: entra al ledger.
5. **`/caso`** — Palancas, supuestos etiquetados, P10–P90, rampa, volante. Cierre: diagnóstico de fuga, tres semanas.
6. **`/defensa`** — Countdown en días hábiles. Un clic: descargo + contrato hasheado. Contradicciones 60/90 y 7/10.
7. **`/direccion`** — Valor confirmado, embudo, holdout de retención, mapa de precios.
8. **`/sap`** — Payload SAP_COM_0057. Clean core.

## Supuestos y fuentes (hoja)

| Input | Default | Tipo | Fuente |
|---|---|---|---|
| Socios | 262.620 | fuente | SSSalud RNEMP jun-2026 |
| Prima media | ARS 420.000 / mes | supuesto | Mix; brokers CABA no son lista |
| Siniestralidad | 82% | supuesto | OMINT no publica P&L |
| Débito incremental | 0,5% | supuesto | Caso hospitalario 6,43% |
| Baja bruta | 16% | supuesto | Caída neta dic-25 → jun-26 |
| Módulo 951 | ARS 435.748,51 | fuente | ANSES Res. 284/2026 |
| USD | 1.525 | fuente | Mayorista 20-oct-2026 |
| Build año 1 | USD 450k | supuesto | Ancla de mercado |

El run-rate a defaults ronda ARS 5,5 B / año (~USD 3,6 M). No se afirma un ingreso de OMINT.

## Línea dura

- Procesamiento local: zxing, Tesseract `spa`, Ed25519, sin LLM externo.
- ARCA / SISA / ReNaPDiS son sandboxes con el *shape* de producción.
- Un documento real se procesa en memoria, se marca “fuera del sandbox” y no se guarda.
- El motor no tiene resultado “rechazar”. Una negativa humana exige cita y segunda firma.
- Diagnósticos ocultos fuera de auditoría médica.

## Stack

FastAPI + SQLite :8018 · React 19 + Vite + Tailwind 4 :5178.
