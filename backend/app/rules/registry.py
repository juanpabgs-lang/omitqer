"""Cited rule catalog. Each rule quotes its source and has an owner."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    source: str
    quote: str
    owner: str
    version: str
    applies_to: str
    conflict: str | None = None
    resolution: str | None = None
    tests: list[str] = field(default_factory=list)


RULES: list[Rule] = [
    Rule(
        id="CARTILLA-4021-A",
        title="Plan con modalidad abierta",
        source="OMINT Cartilla 4021, cap. 6, req. (a), p. 62",
        quote="Estar suscripto a planes que contemplen la modalidad abierta.",
        owner="Prestaciones",
        version="4021",
        applies_to="elegibilidad",
        tests=["genesis_closed_goes_to_review"],
    ),
    Rule(
        id="CARTILLA-4021-B",
        title="Prestación en nomenclador o cobertura del plan",
        source="OMINT Cartilla 4021, cap. 6, req. (b), p. 62",
        quote="Que las prestaciones estén incluidas en el Nomenclador Nacional y/o en la cobertura del plan.",
        owner="Auditoría médica",
        version="4021",
        applies_to="cobertura",
    ),
    Rule(
        id="CARTILLA-4021-C",
        title="No superar topes del plan",
        source="OMINT Cartilla 4021, cap. 6, req. (c), p. 62",
        quote="No haber sobrepasado los topes estipulados para cada plan y prestación.",
        owner="Prestaciones",
        version="4021",
        applies_to="topes",
    ),
    Rule(
        id="CARTILLA-4021-D",
        title="Recibo conforme legislación vigente",
        source="OMINT Cartilla 4021, cap. 6, req. (d), p. 62",
        quote="Presentación de recibo confeccionado de acuerdo con la legislación vigente y normas de OMINT.",
        owner="Reintegros",
        version="4021",
        applies_to="factura",
    ),
    Rule(
        id="CARTILLA-4021-E",
        title="Credencial de asociado",
        source="OMINT Cartilla 4021, cap. 6, req. (e), p. 62",
        quote="Credencial de asociado.",
        owner="Padrón",
        version="4021",
        applies_to="padron",
    ),
    Rule(
        id="CARTILLA-4021-G-90",
        title="Plazo máximo 90 días desde la práctica",
        source="OMINT Cartilla 4021, cap. 6, req. (g), p. 62 · Flyer Reintegros v42",
        quote="El plazo máximo para presentar un reintegro es de 90 días, contados a partir de la realización de la práctica.",
        owner="Reintegros",
        version="4021 / flyer v42",
        applies_to="plazo",
        conflict="CARTILLA-4021-NOTE-B-60",
        resolution="Se aplica 90 días (in dubio pro consumidor, Ley 24.240 art. 37).",
        tests=["days_75_applies_90"],
    ),
    Rule(
        id="CARTILLA-4021-NOTE-B-60",
        title="Vencimiento de documentación a 60 días",
        source="OMINT Cartilla 4021, cap. 6, nota (b), p. 65",
        quote="La documentación indicada tiene como vencimiento 60 (sesenta) días desde la fecha de la prestación… A partir de estas fechas, el beneficiario perderá todo derecho al reclamo de reintegros.",
        owner="Reintegros",
        version="4021",
        applies_to="plazo",
        conflict="CARTILLA-4021-G-90",
        resolution="Contradicción propia de OMINT. El motor aplica 90 días y deja constancia.",
    ),
    Rule(
        id="CARTILLA-4021-NOTE-A",
        title="Original en papel, no fotocopias",
        source="OMINT Cartilla 4021, cap. 6, nota (a), p. 63 · RG AFIP 1415/03",
        quote="Las facturas o recibos tipo B o C deberán presentarse en original (no son válidas las fotocopias).",
        owner="Reintegros",
        version="4021",
        applies_to="factura",
        conflict="ARCA-QR-EFACTURA",
        resolution="Si el comprobante electrónico se constata en ARCA (WSCDC = A), el original digital sustituye al papel.",
    ),
    Rule(
        id="CARTILLA-4021-NOTE-C",
        title="Conversión al tipo vendedor BCRA",
        source="OMINT Cartilla 4021, cap. 6, nota (c), p. 65",
        quote="La conversión del gasto se hará de acuerdo al valor oficial, según el precio vendedor de cambio del Banco Central… correspondiente a la fecha de la prestación.",
        owner="Administración",
        version="4021",
        applies_to="moneda",
    ),
    Rule(
        id="FLYER-V42-7D",
        title="Acreditación a partir de 7 días hábiles",
        source="OMINT Flyer Reintegros v42",
        quote="El reintegro será acreditado… a partir de los 7 días hábiles de presentada la documentación completa.",
        owner="Experiencia",
        version="v42",
        applies_to="sla",
        conflict="FAQ-10D",
        resolution="Se promete 7 días hábiles (documento más reciente y más favorable). El FAQ de 10 días se marca como contradicción.",
    ),
    Rule(
        id="FAQ-10D",
        title="FAQ: depósito a partir de 10 días hábiles",
        source="OMINT FAQ Reintegros (website2 tabid=1691)",
        quote="El depósito se realizará en tu cuenta bancaria, a partir de los 10 días hábiles de recibida la documentación completa.",
        owner="Experiencia",
        version="faq",
        applies_to="sla",
        conflict="FLYER-V42-7D",
        resolution="Contradicción flyer v42 vs FAQ. Se aplica 7 días y se deja constancia.",
    ),
    Rule(
        id="FLYER-V42-CAMPOS",
        title="Campos de la factura ambulatoria",
        source="OMINT Flyer Reintegros v42",
        quote="Fecha de la prestación. Nombre, apellido y número de socio/a. Descripción… Diagnóstico. Firma, aclaración, sello con matrícula del médico y especialidad.",
        owner="Reintegros",
        version="v42",
        applies_to="campos",
        tests=["missing_diagnosis_falta_doc"],
    ),
    Rule(
        id="FLYER-V42-ORDEN",
        title="Orden médica en tratamientos y laboratorio",
        source="OMINT Flyer Reintegros v42",
        quote="En este último caso, deberá figurar cantidad, fecha de las sesiones, importe por sesión y copia/imagen de la orden médica.",
        owner="Reintegros",
        version="v42",
        applies_to="orden",
    ),
    Rule(
        id="FLYER-V42-ESPECIAL",
        title="Quirúrgicos, internación, discapacidad y exterior a mesa",
        source="OMINT Flyer Reintegros v42",
        quote="Para reintegros quirúrgicos, internaciones, discapacidad o gastos en el exterior, consultá en Omint el procedimiento a seguir.",
        owner="Auditoría médica",
        version="v42",
        applies_to="ruteo",
    ),
    Rule(
        id="ARCA-QR-EFACTURA",
        title="QR de factura electrónica RG 4892/2020",
        source="ARCA RG 4892/2020 · JSON v1",
        quote="El código QR contiene ver, fecha, cuit, ptoVta, tipoCmp, nroCmp, importe, moneda, ctz, tipoCodAut, codAut, tipoDocRec, nroDocRec.",
        owner="Integridad",
        version="v1",
        applies_to="factura",
        conflict="CARTILLA-4021-NOTE-A",
    ),
    Rule(
        id="ARCA-WSCDC",
        title="Constatación WSCDC ComprobanteConstatar",
        source="ARCA WSCDC v4 · método ComprobanteConstatar",
        quote="Resultado A (aceptado) o R (rechazado), con Observaciones (100–118 errores, 200 advertencias) y FchProceso.",
        owner="Integridad",
        version="v4",
        applies_to="factura",
        tests=["wscdc_r_goes_to_review"],
    ),
    Rule(
        id="SISA-REFEPS",
        title="Matrícula habilitada en REFEPS",
        source="SISA WS020 getProfesional / WS021 getProfesionales",
        quote="Estado de habilitación de la matrícula, jurisdicción y especialidad del profesional.",
        owner="Prestaciones",
        version="WS020",
        applies_to="profesional",
    ),
    Rule(
        id="RENAPDIS-CUIR",
        title="Orden digital con CUIR",
        source="Res. 1959/2024 · Res. 2214/2025 · ReNaPDiS",
        quote="La receta electrónica se identifica con un Código Único de Identificación de Receta (CUIR).",
        owner="Prestaciones",
        version="illustrative",
        applies_to="orden",
    ),
    Rule(
        id="SSS-951-ART2",
        title="Presunción iuris tantum de incumplimiento",
        source="Res. SSSalud 951/2026 art. 2 (RESOL-2026-951-APN-SSS#MS)",
        quote="La ausencia de respuesta… o sin respaldo documental suficiente… podrán ser valoradas como presunción de incumplimiento.",
        owner="Asuntos regulatorios",
        version="2026",
        applies_to="defensa",
    ),
    Rule(
        id="SSS-951-ART4",
        title="Acreditación fehaciente, suficiente y documentada",
        source="Res. SSSalud 951/2026 art. 4",
        quote="Será responsabilidad… acreditar en forma fehaciente, suficiente y documentada el cumplimiento… El cumplimiento posterior a la INTIMA será considerado regularización extemporánea.",
        owner="Asuntos regulatorios",
        version="2026",
        applies_to="defensa",
    ),
    Rule(
        id="SSS-951-ART6",
        title="Plazos en días hábiles administrativos",
        source="Res. SSSalud 951/2026 art. 6 · Anexo I",
        quote="Los plazos se computarán en días hábiles administrativos. Denuncia e INTIMA: 5 días. Faltas formales: 10 días.",
        owner="Asuntos regulatorios",
        version="2026",
        applies_to="defensa",
    ),
    Rule(
        id="LEY-24240-37",
        title="In dubio pro consumidor",
        source="Ley 24.240 art. 37",
        quote="La interpretación del contrato más favorable para el consumidor.",
        owner="Legales",
        version="1993",
        applies_to="conflictos",
    ),
    Rule(
        id="ROUTER-NUNCA-NIEGA",
        title="El motor no rechaza",
        source="Política Norfront / OMINT demo",
        quote="La IA lee y completa. Las reglas citadas aprueban lo limpio. Una persona decide el resto. No existe un resultado 'rechazar' en el ruteo.",
        owner="Producto",
        version="1",
        applies_to="ruteo",
        tests=["router_has_no_reject"],
    ),
]


REQUIRED_FIELDS: dict[str, list[str]] = {
    "consulta": [
        "fecha",
        "nombre_socio",
        "diagnostico",
        "profesional",
        "detalle",
        "importe",
        "firma_sello",
    ],
    "kinesiologia": [
        "fecha",
        "nombre_socio",
        "diagnostico",
        "profesional",
        "detalle",
        "sesiones",
        "importe",
        "firma_sello",
        "orden_medica",
    ],
    "laboratorio": [
        "fecha",
        "nombre_socio",
        "diagnostico",
        "profesional",
        "detalle",
        "importe",
        "firma_sello",
        "orden_medica",
    ],
    "odontologia": [
        "fecha",
        "nombre_socio",
        "profesional",
        "detalle",
        "pieza",
        "importe",
        "firma_sello",
    ],
    "exterior": [
        "fecha",
        "nombre_socio",
        "profesional",
        "detalle",
        "importe",
        "pasaporte",
        "traduccion",
    ],
}


def rules_as_dicts() -> list[dict]:
    return [
        {
            "id": r.id,
            "title": r.title,
            "source": r.source,
            "quote": r.quote,
            "owner": r.owner,
            "version": r.version,
            "applies_to": r.applies_to,
            "conflict": r.conflict,
            "resolution": r.resolution,
            "tests": r.tests,
        }
        for r in RULES
    ]


def conflicts() -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out = []
    by_id = {r.id: r for r in RULES}
    for r in RULES:
        if not r.conflict:
            continue
        key = tuple(sorted((r.id, r.conflict)))
        if key in seen:
            continue
        seen.add(key)
        other = by_id.get(r.conflict)
        out.append(
            {
                "a": r.id,
                "b": r.conflict,
                "title_a": r.title,
                "title_b": other.title if other else r.conflict,
                "quote_a": r.quote,
                "quote_b": other.quote if other else "",
                "resolution": r.resolution or (other.resolution if other else ""),
            }
        )
    return out
