"""DPA template DOCX builder — Article 28 GDPR.

Generates a customer-ready Data Processing Addendum DOCX programmatically
via ``python-docx``. The template embeds:

- FULKRO controller/processor identifying data (pre-populated)
- 12 sections aligned to Article 28 GDPR sub-articles
- 3 annexes: Sub-procesadores · Medidas técnicas · Categorías de datos
- Merge placeholders for cliente fields: ``{CLIENTE_NOMBRE}``,
  ``{CLIENTE_CIF}``, ``{CLIENTE_DOMICILIO}``, ``{CLIENTE_DPO}``,
  ``{SIGN_DATE}`` — replaced via the substitute_fields helper.

The endpoint streams the in-memory bytes (BytesIO) so we avoid binary
artifacts in the repo and keep a single source of truth in this Python.
"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor


DPA_VERSION = "1.0"

# Canonical sub-encargados live in the RoPA table (``fulkro_ropa_treatments``
# rows with ``is_sub_processor=True``). The DPA Anexo I MUST mirror that list
# (single source of truth · punto #366). When the caller cannot reach the DB
# (e.g. unit test calling ``build_dpa_docx`` directly), this constant is the
# graceful-degradation fallback. It is kept in sync with the RoPA seed
# (``sane_mb9bis_ropa_001``); the live download always passes the DB-derived
# list via ``sub_processors=`` so the published document tracks admin edits.
DEFAULT_SUB_PROCESSORS: list[str] = [
    "Hetzner Online GmbH — hosting (Falkenstein, Alemania · UE).",
    (
        "Postmark / ActiveCampaign LLC — envío de emails transaccionales "
        "(EU Data Region)."
    ),
    (
        "Anthropic PBC — modelo de lenguaje Claude (Estados Unidos, con "
        "replicación en Frankfurt) bajo DPA + Cláusulas Contractuales "
        "Tipo 2021/914."
    ),
    "360dialog GmbH — gateway WhatsApp Business (Alemania · UE).",
    (
        "MinIO — almacenamiento de objetos auto-hospedado por FULKRO en la "
        "infraestructura de Hetzner (no constituye sub-encargado externo "
        "independiente)."
    ),
]

# Fields that callers can pre-populate. Unknown names render as the
# placeholder itself so the cliente sees what to fill.
DEFAULT_FIELDS: dict[str, str] = {
    "CLIENTE_NOMBRE": "[NOMBRE LEGAL DEL CLIENTE]",
    "CLIENTE_CIF": "[CIF / NIF DEL CLIENTE]",
    "CLIENTE_DOMICILIO": "[DOMICILIO SOCIAL DEL CLIENTE]",
    "CLIENTE_DPO": "[DPO O CONTACTO PRIVACIDAD DEL CLIENTE]",
    "SIGN_DATE": "[FECHA DE FIRMA]",
    # Identidad fiscal FULKRO (FUENTE ÚNICA · punto #44). El caller
    # (dpa_api) inyecta los valores reales desde get_fiscal_identity;
    # estos defaults son degradación elegante (sin placeholder de CIF).
    "FULKRO_NOMBRE": "Marcos Mata García",
    "FULKRO_CIF": "",
    "FULKRO_DOMICILIO": "Madrid (España)",
}


def build_dpa_docx(
    fields: dict[str, str] | None = None,
    sub_processors: list[str] | None = None,
) -> BytesIO:
    """Return a ready-to-download DPA as an in-memory ``.docx`` stream.

    ``sub_processors`` is the canonical sub-encargados list (one display
    line per processor) sourced from the RoPA table. When ``None`` the
    builder falls back to ``DEFAULT_SUB_PROCESSORS`` so direct/offline
    callers still render a valid Anexo I.
    """
    merged = {**DEFAULT_FIELDS, **(fields or {})}
    subprocs = sub_processors if sub_processors else DEFAULT_SUB_PROCESSORS

    def fmt(text: str) -> str:
        for key, value in merged.items():
            text = text.replace("{" + key + "}", value)
        return text

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    # Title
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("CONTRATO DE ENCARGO DEL TRATAMIENTO (DPA)")
    run.bold = True
    run.font.size = Pt(16)
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = subtitle.add_run(
        f"Artículo 28 del Reglamento (UE) 2016/679 · Versión {DPA_VERSION}"
    )
    sub_run.italic = True
    sub_run.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
    doc.add_paragraph()

    # 1. Partes
    _add_section(
        doc,
        "1. Partes",
        [
            (
                "RESPONSABLE DEL TRATAMIENTO ('el Cliente'): "
                f"{fmt('{CLIENTE_NOMBRE}')}, con CIF {fmt('{CLIENTE_CIF}')} y "
                f"domicilio social en {fmt('{CLIENTE_DOMICILIO}')}. Contacto "
                f"para asuntos de privacidad: {fmt('{CLIENTE_DPO}')}."
            ),
            (
                "ENCARGADO DEL TRATAMIENTO ('FULKRO'): "
                f"{fmt('{FULKRO_NOMBRE}')}, con CIF {fmt('{FULKRO_CIF}')}, "
                f"con domicilio profesional en {fmt('{FULKRO_DOMICILIO}')}. "
                "Contacto DPO: dpo@fulkro.es. Actividad: "
                "consultoría de servicios IT especializada en el Esquema "
                "Nacional de Seguridad (RD 311/2022)."
            ),
            (
                f"Ambas partes suscriben el presente contrato con fecha "
                f"{fmt('{SIGN_DATE}')} a los efectos previstos en el "
                "artículo 28 del Reglamento (UE) 2016/679 ('RGPD') y la Ley "
                "Orgánica 3/2018, de 5 de diciembre, de Protección de Datos "
                "Personales y garantía de los derechos digitales ('LOPDGDD')."
            ),
        ],
    )

    # 2. Objeto y finalidad
    _add_section(
        doc,
        "2. Objeto y finalidad (Art. 28.3 RGPD)",
        [
            (
                "Este contrato regula el tratamiento de datos personales que "
                "FULKRO realiza, por cuenta del Cliente, en el marco de los "
                "servicios de consultoría e implantación ENS contratados "
                "mediante el correspondiente Contrato de Servicios."
            ),
            (
                "El tratamiento se ciñe a: (i) la gestión de proyectos del "
                "Cliente en la plataforma FULKRO; (ii) la generación, firma "
                "y archivo de documentos derivados (políticas, evidencias, "
                "informes); (iii) las comunicaciones operacionales necesarias "
                "para la prestación del servicio."
            ),
        ],
    )

    # 3. Duración
    _add_section(
        doc,
        "3. Duración (Art. 28.3 RGPD)",
        [
            (
                "El presente DPA estará en vigor durante toda la vigencia del "
                "Contrato de Servicios suscrito entre las partes. Una vez "
                "extinguido el Contrato de Servicios, FULKRO conservará "
                "exclusivamente los datos imprescindibles para acreditar el "
                "cumplimiento ante auditorías ENS (art. 24.1 RD 311/2022) "
                "durante un plazo máximo de 7 años, momento tras el cual los "
                "datos serán anonimizados o suprimidos definitivamente."
            ),
        ],
    )

    # 4. Naturaleza y finalidad del tratamiento
    _add_section(
        doc,
        "4. Naturaleza y finalidad del tratamiento (Art. 28.3.a RGPD)",
        [
            (
                "FULKRO tratará los datos del Cliente únicamente para las "
                "siguientes finalidades operativas: extracción y análisis "
                "automatizado de documentos provistos por el Cliente, "
                "generación de informes y políticas, archivo de evidencias "
                "documentales, envío de notificaciones operacionales por los "
                "canales consentidos por los interesados y registro de "
                "operaciones en el log de auditoría."
            ),
        ],
    )

    # 5. Tipo de datos y categorías de interesados
    _add_section(
        doc,
        "5. Tipo de datos personales y categorías de interesados (Art. 28.3.b RGPD)",
        [
            (
                "Categorías de datos tratados: datos identificativos (nombre, "
                "apellidos), datos de contacto profesional (correo "
                "electrónico, teléfono), datos laborales (cargo, "
                "organización), datos técnicos del sistema del Cliente "
                "(direcciones IP, identificadores técnicos) cuando aparecen "
                "incidentalmente en evidencias documentales."
            ),
            (
                "Categorías de interesados: empleados del Cliente, personas "
                "de contacto designadas, y excepcionalmente terceros "
                "mencionados en la documentación aportada por el Cliente."
            ),
            (
                "FULKRO no tratará categorías especiales de datos (Art. 9 "
                "RGPD) ni datos relativos a condenas o infracciones (Art. 10 "
                "RGPD) salvo instrucción expresa documentada del Cliente y "
                "previa adopción de las garantías reforzadas que correspondan."
            ),
        ],
    )

    # 6. Obligaciones del encargado
    _add_section(
        doc,
        "6. Obligaciones de FULKRO como encargado (Art. 28.3 RGPD)",
        [
            "FULKRO se compromete a:",
        ],
    )
    _add_numbered(
        doc,
        [
            (
                "Tratar los datos personales únicamente siguiendo "
                "instrucciones documentadas del Cliente (Art. 28.3.a)."
            ),
            (
                "Garantizar que las personas autorizadas para tratar los "
                "datos personales se han comprometido a respetar la "
                "confidencialidad o están sujetas a una obligación legal de "
                "confidencialidad (Art. 28.3.b)."
            ),
            (
                "Tomar todas las medidas necesarias de conformidad con el "
                "Art. 32 RGPD, según se detalla en el Anexo II."
            ),
            (
                "Respetar las condiciones del Art. 28.2 y 28.4 RGPD para "
                "recurrir a sub-encargados, conforme al Anexo I."
            ),
            (
                "Asistir al Cliente, teniendo en cuenta la naturaleza del "
                "tratamiento, mediante medidas técnicas y organizativas "
                "apropiadas, en el cumplimiento de su obligación de responder "
                "a las solicitudes que tengan por objeto el ejercicio de los "
                "derechos de los interesados (Art. 28.3.e). FULKRO expone "
                "endpoints directos a los interesados en el portal cliente: "
                "/portal/rgpd/access, /portal/rgpd/erasure, "
                "/portal/rgpd/portability."
            ),
            (
                "Ayudar al Cliente a garantizar el cumplimiento de las "
                "obligaciones establecidas en los Artículos 32 a 36 RGPD "
                "(seguridad, notificación de violaciones, evaluaciones de "
                "impacto y consultas previas) — Art. 28.3.f."
            ),
            (
                "A elección del Cliente, suprimir o devolver todos los datos "
                "personales una vez finalice la prestación de los servicios, "
                "y suprimir las copias existentes salvo obligación legal de "
                "conservarlas (Art. 28.3.g)."
            ),
            (
                "Poner a disposición del Cliente toda la información "
                "necesaria para demostrar el cumplimiento de las obligaciones "
                "del Art. 28 RGPD, así como permitir y contribuir a la "
                "realización de auditorías, incluidas inspecciones, por parte "
                "del Cliente o de un auditor autorizado por éste (Art. 28.3.h)."
            ),
        ],
    )

    # 7. Sub-encargados
    _add_section(
        doc,
        "7. Sub-encargados (Art. 28.2 y 28.4 RGPD)",
        [
            (
                "El Cliente autoriza, con carácter general, a FULKRO a "
                "recurrir a los sub-encargados listados en el Anexo I. "
                "FULKRO publica la lista actualizada de sub-encargados en "
                "https://fulkro.es/sub-processors. El Cliente puede "
                "suscribirse a notificaciones por correo electrónico cuando "
                "la lista cambie (mecanismo del Art. 28.2 RGPD)."
            ),
            (
                "FULKRO informará al Cliente de cualquier cambio previsto "
                "(incorporación o sustitución de un sub-encargado) con un "
                "preaviso no inferior a 30 días, durante el cual el Cliente "
                "podrá oponerse motivadamente. En caso de oposición, las "
                "partes negociarán de buena fe una solución equivalente o, "
                "en su defecto, el Cliente podrá resolver el Contrato de "
                "Servicios sin penalización."
            ),
            (
                "Con cada sub-encargado, FULKRO suscribirá un contrato que "
                "imponga obligaciones equivalentes a las del presente DPA, "
                "particularmente en cuanto a garantías de seguridad técnicas "
                "y organizativas (Art. 28.4)."
            ),
        ],
    )

    # 8. Medidas de seguridad
    _add_section(
        doc,
        "8. Medidas de seguridad (Art. 32 RGPD)",
        [
            (
                "FULKRO aplica las medidas técnicas y organizativas "
                "descritas en el Anexo II del presente contrato, que "
                "incluyen, sin carácter limitativo: cifrado en tránsito y "
                "en reposo, segmentación multi-tenant mediante Row-Level "
                "Security, autenticación reforzada (2FA TOTP) para el "
                "personal administrador, firma electrónica avanzada "
                "Ed25519 del log de auditoría, copias de seguridad cifradas "
                "con prueba mensual de restauración, separación de claves "
                "criptográficas en sistemas independientes."
            ),
        ],
    )

    # 9. Derechos de los interesados
    _add_section(
        doc,
        "9. Derechos de los interesados (Art. 28.3.e RGPD)",
        [
            (
                "FULKRO pone a disposición de los empleados y contactos del "
                "Cliente que dispongan de credenciales del portal cliente "
                "los siguientes mecanismos directos para el ejercicio de sus "
                "derechos:"
            ),
            (
                "• Derecho de acceso (Art. 15 RGPD): GET "
                "/api/v1/portal/rgpd/access → descarga ZIP estructurado."
            ),
            (
                "• Derecho de supresión (Art. 17 RGPD): POST "
                "/api/v1/portal/rgpd/erasure → workflow de eliminación con "
                "anonimización tombstone."
            ),
            (
                "• Derecho de portabilidad (Art. 20 RGPD): GET "
                "/api/v1/portal/rgpd/portability → formato JSON estructurado."
            ),
            (
                "En todos los casos FULKRO se compromete a tramitar la "
                "solicitud en un plazo máximo de un mes (Art. 12.3 RGPD), "
                "prorrogable por dos meses adicionales si la complejidad o "
                "el número de solicitudes lo justifica."
            ),
        ],
    )

    # 10. Notificación de violaciones
    _add_section(
        doc,
        "10. Notificación de violaciones de seguridad (Art. 33 RGPD)",
        [
            (
                "FULKRO notificará al Cliente, sin dilación indebida y, a "
                "más tardar, dentro de las 72 horas siguientes a tener "
                "conocimiento de una violación de la seguridad que afecte a "
                "datos personales tratados por cuenta del Cliente. La "
                "notificación contendrá la información requerida por el Art. "
                "33.3 RGPD: naturaleza de la violación, categorías y número "
                "aproximado de interesados y registros afectados, "
                "consecuencias probables, medidas adoptadas o propuestas."
            ),
            (
                "FULKRO mantiene un registro interno de incidencias de "
                "seguridad (workflow administrativo "
                "/admin/compliance/breach) que automatiza el envío de la "
                "notificación a la AEPD cuando proceda."
            ),
        ],
    )

    # 11. Post-contrato
    _add_section(
        doc,
        "11. Finalización del tratamiento (Art. 28.3.g RGPD)",
        [
            (
                "Una vez extinguido el Contrato de Servicios, el Cliente "
                "podrá optar por: (i) la devolución de sus datos en formato "
                "estructurado (ZIP cross-motor) a través del endpoint "
                "/portal/rgpd/access; (ii) la supresión definitiva, salvo "
                "respecto de los datos cuya conservación venga impuesta por "
                "obligación legal (en particular, evidencias ENS sujetas al "
                "plazo de 7 años del art. 24.1 RD 311/2022, retenidas en "
                "forma anonimizada agregada)."
            ),
        ],
    )

    # 12. Jurisdicción
    _add_section(
        doc,
        "12. Ley aplicable y jurisdicción",
        [
            (
                "El presente DPA se rige por la legislación española y, en "
                "particular, por el RGPD y la LOPDGDD. Para la resolución "
                "de cualquier controversia derivada del mismo, las partes "
                "se someten a los Juzgados y Tribunales de Madrid, con "
                "renuncia expresa a cualquier otro fuero que pudiera "
                "corresponderles."
            ),
        ],
    )

    # Page break + Anexos
    doc.add_page_break()
    _add_section(
        doc,
        "Anexo I · Sub-encargados autorizados",
        [
            (
                "FULKRO ha autorizado los siguientes sub-encargados, todos "
                "ellos con DPA firmado conforme al Art. 28 RGPD y, en caso "
                "de transferencias internacionales, con Cláusulas "
                "Contractuales Tipo (Decisión 2021/914 de la Comisión)."
            ),
            *[f"{idx}. {line}" for idx, line in enumerate(subprocs, start=1)],
            (
                "Lista actualizada y permanentemente consultable en "
                "https://fulkro.es/sub-processors."
            ),
        ],
    )

    _add_section(
        doc,
        "Anexo II · Medidas técnicas y organizativas (Art. 32 RGPD)",
        [
            (
                "Medidas técnicas:"
            ),
            "• Cifrado en tránsito TLS 1.3 (HSTS forzado).",
            (
                "• Cifrado en reposo de la base de datos PostgreSQL "
                "(Transparent Data Encryption) y del almacén de objetos "
                "MinIO (server-side encryption AES-256-GCM)."
            ),
            (
                "• Segmentación multi-tenant mediante Row-Level Security en "
                "PostgreSQL, con cobertura supervisada por el sistema de "
                "monitorización interna (check rls_coverage_percentage)."
            ),
            (
                "• Pseudonimización del contenido enviado al modelo de "
                "lenguaje (T004) cuando contenga identificadores directos."
            ),
            (
                "• Firma electrónica Ed25519 del log de auditoría con "
                "sellado horario diario."
            ),
            (
                "• Copias de seguridad diarias cifradas con prueba mensual "
                "automatizada de restauración (motor M26)."
            ),
            "Medidas organizativas:",
            (
                "• Autenticación reforzada 2FA TOTP para el personal "
                "administrador."
            ),
            (
                "• Acceso al portal cliente mediante magic-link firmado "
                "Ed25519 (caducidad 72 horas, un solo uso)."
            ),
            (
                "• Procedimiento documentado de gestión de incidentes con "
                "notificación al Cliente en 72 horas (sección 10 del DPA)."
            ),
            (
                "• Revisión anual del registro de actividades (RoPA · Art. "
                "30 RGPD) y de las políticas internas ISO 27001:2022."
            ),
            (
                "• Auditoría externa ENS prevista al amparo del art. 31 RD "
                "311/2022."
            ),
        ],
    )

    _add_section(
        doc,
        "Anexo III · Categorías de datos y operaciones de tratamiento",
        [
            (
                "Las categorías de datos personales tratadas y las "
                "operaciones de tratamiento se corresponden, una a una, con "
                "los registros del Registro de Actividades de Tratamiento "
                "(RoPA, Art. 30 RGPD) que FULKRO mantiene actualizado y "
                "audita anualmente. El Cliente puede solicitar copia del "
                "extracto del RoPA relativo a los tratamientos efectuados "
                "por cuenta suya escribiendo a dpo@fulkro.es."
            ),
        ],
    )

    # Signature block
    doc.add_page_break()
    sign_para = doc.add_paragraph()
    sign_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    sign_run = sign_para.add_run("Firmas")
    sign_run.bold = True
    sign_run.font.size = Pt(14)

    table = doc.add_table(rows=4, cols=2)
    table.cell(0, 0).text = "Por el Cliente (Responsable)"
    table.cell(0, 1).text = "Por FULKRO (Encargado)"
    table.cell(1, 0).text = fmt("Nombre: {CLIENTE_NOMBRE}")
    table.cell(1, 1).text = "Nombre: Marcos Mata García"
    table.cell(2, 0).text = fmt("DPO/Contacto: {CLIENTE_DPO}")
    table.cell(2, 1).text = "DPO/Contacto: dpo@fulkro.es"
    table.cell(3, 0).text = fmt("Fecha y firma: {SIGN_DATE}")
    table.cell(3, 1).text = fmt("Fecha y firma: {SIGN_DATE}")
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for r in paragraph.runs:
                    r.font.size = Pt(10.5)

    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    foot_run = footer.add_run(
        f"DPA FULKRO · Versión {DPA_VERSION} · "
        f"Generado el {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    )
    foot_run.italic = True
    foot_run.font.size = Pt(9)
    foot_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def _add_section(doc: Document, heading: str, paragraphs: list[str]) -> None:
    h = doc.add_paragraph()
    h_run = h.add_run(heading)
    h_run.bold = True
    h_run.font.size = Pt(12)
    h_run.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)
    for body in paragraphs:
        p = doc.add_paragraph(body)
        p.paragraph_format.space_after = Pt(6)


def _add_numbered(doc: Document, items: list[str]) -> None:
    for idx, item in enumerate(items, start=1):
        p = doc.add_paragraph(f"{idx}. {item}")
        p.paragraph_format.left_indent = Pt(18)
        p.paragraph_format.space_after = Pt(4)
