"""FULKRO corpus catalog.

Single source of truth for the documents that compose the FULKRO knowledge
base. Each entry describes the source (where to fetch the document), its
metadata (priority, category, ENS measures covered) and the local file path
where the ingester expects to find the downloaded artifact.

The catalog is consumed by:
- ``scripts/corpus_download.py``      to know which sources to attempt
- ``scripts/corpus_ingest.py``        to persist into ``knowledge_documents``
- ``scripts/corpus_audit.py``         to compare vs. the DB
- The ``corpus`` API surface          to expose status to the operator

Status semantics:
- ``ingested``         already in the DB with chunks + embeddings
- ``pending_auto``     URL public, automated download viable
- ``pending_manual``   anti-bot / login required, Marcos uploads manually
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal


SourceType = Literal[
    "boe", "eur_lex", "ccn_stic", "iso", "nist", "owasp",
    "aepd", "magerit", "pce", "incibe", "pci_dss", "other",
]
Priority = Literal["critical", "high", "medium", "low"]
Status = Literal["ingested", "pending_auto", "pending_manual"]
Category = Literal[
    "normativa_ens", "guia_tecnica", "estandar_internacional",
    "legislacion", "hardening", "metodologia", "perfil_cumplimiento",
    "guia_aepd", "guia_incibe", "manual_herramienta",
]


@dataclass(frozen=True)
class CorpusDoc:
    """One document in the FULKRO corpus catalog."""

    source_id: str                         # canonical short code, e.g. "CCN-STIC-804"
    title: str
    source_type: SourceType
    url: str
    priority: Priority
    status: Status
    category: Category
    file_path: str                         # relative under ~/.fulkro/corpus_cache/
    description: str
    ens_measures_covered: list[str] = field(default_factory=lambda: ["*"])
    language: str = "es"
    version: str = "2025"

    def to_dict(self) -> dict:
        return asdict(self)


# === GROUP 0: docs already ingested (reales) ================================
_INGESTED: list[CorpusDoc] = [
    CorpusDoc("RD-311-2022", "Real Decreto 311/2022 ENS", "boe",
              "https://www.boe.es/boe/dias/2022/05/04/pdfs/BOE-A-2022-7191.pdf",
              "critical", "ingested", "normativa_ens",
              "auto/boe/rd_311_2022.pdf",
              "Marco normativo principal del Esquema Nacional de Seguridad",
              ["*"]),
    CorpusDoc("BOE-ITS-CONFORMIDAD", "ITS Conformidad ENS", "boe",
              "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2016-10109",
              "critical", "ingested", "normativa_ens",
              "auto/boe/its_conformidad.html",
              "Instrucción Técnica de Seguridad de Conformidad con el ENS"),
    CorpusDoc("BOE-ITS-ESTADO", "ITS Estado de la Seguridad", "boe",
              "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2016-10108",
              "critical", "ingested", "normativa_ens",
              "auto/boe/its_estado_seguridad.html",
              "Instrucción Técnica del Informe del Estado de la Seguridad"),
    CorpusDoc("BOE-ITS-AUDITORIA", "ITS Auditoría ENS", "boe",
              "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2018-4573",
              "critical", "ingested", "normativa_ens",
              "auto/boe/its_auditoria.html",
              "Instrucción Técnica de Auditoría de la Seguridad"),
    CorpusDoc("BOE-ITS-INCIDENTES", "ITS Notificación de Incidentes", "boe",
              "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2018-5370",
              "high", "ingested", "normativa_ens",
              "auto/boe/its_incidentes.html",
              "Instrucción Técnica de Notificación de Incidentes"),
    CorpusDoc("LOPDGDD", "Ley Orgánica 3/2018 LOPDGDD", "boe",
              "https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673",
              "critical", "ingested", "legislacion",
              "auto/boe/lopdgdd.html",
              "Ley Orgánica de Protección de Datos y Garantía de Derechos Digitales"),
    CorpusDoc("BOE-LEY-39-2015", "Ley 39/2015 PAC", "boe",
              "https://www.boe.es/buscar/act.php?id=BOE-A-2015-10565",
              "high", "ingested", "legislacion",
              "auto/boe/ley_39_2015.html",
              "Procedimiento Administrativo Común"),
    CorpusDoc("BOE-LEY-40-2015", "Ley 40/2015 RJSP", "boe",
              "https://www.boe.es/buscar/act.php?id=BOE-A-2015-10566",
              "high", "ingested", "legislacion",
              "auto/boe/ley_40_2015.html",
              "Régimen Jurídico del Sector Público"),
    CorpusDoc("RGPD", "Reglamento (UE) 2016/679 RGPD", "eur_lex",
              "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32016R0679",
              "critical", "ingested", "legislacion",
              "auto/eur_lex/rgpd_2016_679.html",
              "Reglamento General de Protección de Datos"),
    CorpusDoc("AI-ACT", "Reglamento (UE) 2024/1689 IA", "eur_lex",
              "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32024R1689",
              "high", "ingested", "legislacion",
              "auto/eur_lex/ai_act_2024_1689.html",
              "Reglamento europeo de Inteligencia Artificial"),
    CorpusDoc("CRA", "Reglamento (UE) 2024/2847 CRA", "eur_lex",
              "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32024R2847",
              "high", "ingested", "legislacion",
              "auto/eur_lex/cra_2024_2847.html",
              "Cyber Resilience Act"),
    CorpusDoc("MAGERIT-V3", "MAGERIT v3 Resumen", "magerit",
              "https://administracionelectronica.gob.es/pae_Home/pae_Documentacion/pae_Metodolog/pae_Magerit.html",
              "critical", "ingested", "metodologia",
              "auto/magerit/magerit_v3_resumen.html",
              "Metodología de Análisis y Gestión de Riesgos"),
    CorpusDoc("CCN-STIC-804-CACHE", "CCN-STIC 804 Mirror", "ccn_stic",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad/2-uncategorised/525-ccn-stic-804-medidas-de-implantacion.html",
              "critical", "ingested", "guia_tecnica",
              "auto/ccn_stic/ccn_stic_804_cache.html",
              "Guía de implantación del Anexo II del ENS (versión cacheada)"),
]
# Ejecutable 8 OLA 0 (#21): RETIRADO el padding de 27 docs sintéticos
# (`INGESTED-NN` → example.invalid). Inflaban el conteo de cobertura ("40
# ingested") con documentos que no existen ni en el object store ni en el RAG,
# falseando los reportes de corpus. _INGESTED queda con los documentos REALES.


# === GROUP 1: EUR-Lex (extras) ==============================================
_EUR_LEX: list[CorpusDoc] = [
    # Sub-lote 1.B.5.2 · ingested via ccn_pdf_ingest.py (DB code = "UE-NIS2")
    CorpusDoc("NIS2", "Directiva (UE) 2022/2555 NIS2", "eur_lex",
              "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32022L2555",
              "critical", "ingested", "legislacion",
              "manual/eur_lex/nis2_2022_2555.pdf",
              "Directiva NIS2 sobre seguridad de redes y sistemas de información",
              ["op.exp.7", "op.mon.3"]),
    # Sub-lote 1.B.5.2 · ingested via ccn_pdf_ingest.py (DB code = "UE-DORA")
    CorpusDoc("DORA", "Reglamento (UE) 2022/2554 DORA", "eur_lex",
              "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32022R2554",
              "critical", "ingested", "legislacion",
              "manual/eur_lex/dora_2022_2554.pdf",
              "Resiliencia operativa digital del sector financiero",
              ["op.cont.1", "op.cont.2", "op.ext.2"]),
    # Sub-lote 1.B.5.2 · ingested via ccn_pdf_ingest.py (DB code = "UE-EIDAS")
    CorpusDoc("eIDAS", "Reglamento (UE) 910/2014 eIDAS", "eur_lex",
              "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32014R0910",
              "high", "ingested", "legislacion",
              "manual/eur_lex/eidas_910_2014.pdf",
              "Identificación electrónica y servicios de confianza",
              ["mp.info.4", "mp.info.5"]),
    CorpusDoc("EUR-LEX-NIS2-TRANSP", "NIS2 transposición española (anteproyecto)",
              "eur_lex",
              "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32022L2555#transposition",
              "high", "pending_manual", "legislacion",
              "manual/eur_lex/nis2_transposicion_es.pdf",
              "Anteproyecto de transposición española de NIS2 al ordenamiento interno",
              ["op.exp.7"]),
]


# === GROUP 2: CCN-STIC Serie 800 ============================================
# Sub-lote 1.B.5.2 · 9/10 ingested via ccn_pdf_ingest.py (CCN-STIC-800 a 808).
# La tabla XLSX 808-III queda pending (formato spreadsheet · pipeline distinto).
_CCN_STIC_800: list[CorpusDoc] = [
    CorpusDoc("CCN-STIC-800", "Glosario de términos ENS", "ccn_stic",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
              "high", "ingested", "guia_tecnica",
              "manual/ccn/stic_serie_800/ccn_stic_800_glosario.pdf",
              "Glosario oficial de términos del ENS"),
    CorpusDoc("CCN-STIC-801", "Responsabilidades y Funciones ENS", "ccn_stic",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
              "critical", "ingested", "guia_tecnica",
              "manual/ccn/stic_serie_800/ccn_stic_801_responsabilidades.pdf",
              "Asignación de roles y funciones de seguridad en el ENS",
              ["org.2", "org.3", "org.4"]),
    CorpusDoc("CCN-STIC-802", "Auditoría en el ENS", "ccn_stic",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
              "critical", "ingested", "guia_tecnica",
              "manual/ccn/stic_serie_800/ccn_stic_802_auditoria.pdf",
              "Guía de auditoría de cumplimiento del ENS"),
    CorpusDoc("CCN-STIC-803", "Valoración de Sistemas ENS", "ccn_stic",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
              "critical", "ingested", "guia_tecnica",
              "manual/ccn/stic_serie_800/ccn_stic_803_valoracion.pdf",
              "Metodología de categorización (D/I/C/A/T) y dimensiones del sistema"),
    CorpusDoc("CCN-STIC-804", "Medidas de implantación ENS", "ccn_stic",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
              "critical", "ingested", "guia_tecnica",
              "manual/ccn/stic_serie_800/ccn_stic_804_medidas.pdf",
              "Guía oficial CCN para implantar el Anexo II del ENS",
              ["*"]),
    CorpusDoc("CCN-STIC-805", "Política de Seguridad ENS", "ccn_stic",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
              "critical", "ingested", "guia_tecnica",
              "manual/ccn/stic_serie_800/ccn_stic_805_politica.pdf",
              "Modelo y contenidos mínimos de la Política de Seguridad",
              ["org.1"]),
    CorpusDoc("CCN-STIC-806", "Plan de Adecuación ENS", "ccn_stic",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
              "critical", "ingested", "guia_tecnica",
              "manual/ccn/stic_serie_800/ccn_stic_806_plan_adecuacion.pdf",
              "Estructura y contenidos del Plan de Adecuación al ENS"),
    CorpusDoc("CCN-STIC-807", "Criptología en el ENS", "ccn_stic",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
              "high", "ingested", "guia_tecnica",
              "manual/ccn/stic_serie_800/ccn_stic_807_criptologia.pdf",
              "Algoritmos y mecanismos criptográficos aprobados por el CCN",
              ["mp.info.3", "mp.com.2"]),
    CorpusDoc("CCN-STIC-808", "Verificación del cumplimiento ENS", "ccn_stic",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
              "critical", "ingested", "guia_tecnica",
              "manual/ccn/stic_serie_800/ccn_stic_808_verificacion.pdf",
              "Checklist de verificación con grados L0-L5 por medida"),
    CorpusDoc("CCN-STIC-808-III", "Tabla verificación cumplimiento (xlsx)", "ccn_stic",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
              "high", "pending_manual", "guia_tecnica",
              "manual/ccn/stic_serie_800/ccn_stic_808_iii_tabla.xlsx",
              "Plantilla XLSX de verificación de cumplimiento"),
    # #30 · CCN-STIC 809 · base del cierre BÁSICA (Declaración de Conformidad +
    # distintivo · Anexo A) · sin esto el copiloto no puede fundamentar cómo se
    # cierra BÁSICA (autodeclaración firmada por Dirección). pending_manual: el
    # PDF lo descarga Marcos (CCN-CERT login) y se ingesta vía ccn_pdf_ingest.
    CorpusDoc("CCN-STIC-809", "Declaración de Conformidad del ENS", "ccn_stic",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
              "critical", "pending_manual", "guia_tecnica",
              "manual/ccn/stic_serie_800/ccn_stic_809_declaracion_conformidad.pdf",
              "Declaración de Conformidad + distintivo (Anexo A) · cierre BÁSICA "
              "por autodeclaración firmada por Dirección (clave Premisa #1)"),
]


# === GROUP 3: BOE / Legislación española extra ==============================
_BOE_EXTRA: list[CorpusDoc] = [
    CorpusDoc("Ley-8-2011", "Ley 8/2011 Infraestructuras Críticas", "boe",
              "https://www.boe.es/buscar/act.php?id=BOE-A-2011-7630",
              "high", "pending_manual", "legislacion",
              "manual/boe/ley_8_2011_pic.html",
              "Protección de infraestructuras críticas españolas"),
    CorpusDoc("Ley-41-2002", "Ley 41/2002 Autonomía del Paciente", "boe",
              "https://www.boe.es/buscar/act.php?id=BOE-A-2002-22188",
              "medium", "pending_manual", "legislacion",
              "manual/boe/ley_41_2002.html",
              "Derechos y obligaciones del paciente y datos de salud",
              ["mp.info.1"]),
    CorpusDoc("Ley-11-2007", "Ley 11/2007 Acceso electrónico (derogada)",
              "boe",
              "https://www.boe.es/buscar/act.php?id=BOE-A-2007-12352",
              "low", "pending_manual", "legislacion",
              "manual/boe/ley_11_2007.html",
              "Acceso electrónico de los ciudadanos a los servicios públicos"),
    CorpusDoc("RD-3-2010", "Real Decreto 3/2010 ENS original", "boe",
              "https://www.boe.es/buscar/act.php?id=BOE-A-2010-1330",
              "low", "pending_manual", "legislacion",
              "manual/boe/rd_3_2010.html",
              "ENS original (derogado, referencia histórica)"),
    CorpusDoc("RD-951-2015", "Real Decreto 951/2015 modificación ENS", "boe",
              "https://www.boe.es/buscar/act.php?id=BOE-A-2015-11881",
              "low", "pending_manual", "legislacion",
              "manual/boe/rd_951_2015.html",
              "Modificación del ENS por RD 951/2015 (derogado por 311/2022)"),
    CorpusDoc("Ley-39-2015-CONSOLIDADA", "Ley 39/2015 consolidada", "boe",
              "https://www.boe.es/buscar/act.php?id=BOE-A-2015-10565&p=20240101",
              "medium", "pending_manual", "legislacion",
              "manual/boe/ley_39_2015_consolidada.html",
              "Versión consolidada vigente del PAC"),
    CorpusDoc("LSSI", "Ley 34/2002 LSSI-CE", "boe",
              "https://www.boe.es/buscar/act.php?id=BOE-A-2002-13758",
              "medium", "pending_manual", "legislacion",
              "manual/boe/lssi_34_2002.html",
              "Ley de Servicios de la Sociedad de la Información"),
    CorpusDoc("REAL-DECRETO-LEY-12-2018", "RD-Ley 12/2018 NIS",
              "boe",
              "https://www.boe.es/buscar/act.php?id=BOE-A-2018-12257",
              "high", "pending_manual", "legislacion",
              "manual/boe/rd_ley_12_2018.html",
              "Transposición original NIS al ordenamiento español"),
]


# === GROUP 4: ISO / NIST ====================================================
_STANDARDS: list[CorpusDoc] = [
    CorpusDoc("ISO-27001", "ISO/IEC 27001:2022 (resumen público)", "iso",
              "https://www.iso.org/standard/27001",
              "critical", "pending_manual", "estandar_internacional",
              "manual/iso/iso_27001_2022_resumen.pdf",
              "SGSI — requisitos. Resumen público y mapeo con ENS"),
    CorpusDoc("ISO-27002", "ISO/IEC 27002:2022 (resumen público)", "iso",
              "https://www.iso.org/standard/27002",
              "high", "pending_manual", "estandar_internacional",
              "manual/iso/iso_27002_2022_resumen.pdf",
              "Controles de seguridad de la información"),
    CorpusDoc("ISO-27005", "ISO/IEC 27005:2022", "iso",
              "https://www.iso.org/standard/27005",
              "high", "pending_manual", "estandar_internacional",
              "manual/iso/iso_27005_2022_resumen.pdf",
              "Gestión de riesgos de seguridad de la información"),
    CorpusDoc("ISO-22301", "ISO 22301:2019 BCMS", "iso",
              "https://www.iso.org/standard/22301",
              "medium", "pending_manual", "estandar_internacional",
              "manual/iso/iso_22301_2019_resumen.pdf",
              "Continuidad de negocio (BCMS)"),
    CorpusDoc("NIST-CSF", "NIST Cybersecurity Framework v2.0", "nist",
              "https://www.nist.gov/cyberframework",
              "high", "pending_manual", "estandar_internacional",
              "manual/nist/nist_csf_v2.pdf",
              "Marco de ciberseguridad NIST"),
    CorpusDoc("NIST-800-53", "NIST SP 800-53 Rev.5", "nist",
              "https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final",
              "high", "pending_manual", "estandar_internacional",
              "manual/nist/nist_800_53_r5.pdf",
              "Catálogo de controles NIST 800-53"),
    CorpusDoc("OWASP-WSTG", "OWASP Web Security Testing Guide v4.2", "owasp",
              "https://owasp.org/www-project-web-security-testing-guide/",
              "high", "pending_auto", "guia_tecnica",
              "manual/owasp/owasp_wstg_v4_2.pdf",
              "Guía de pentesting web OWASP",
              ["mp.sw.2"]),
    CorpusDoc("OWASP-ASVS", "OWASP ASVS v4.0", "owasp",
              "https://owasp.org/www-project-application-security-verification-standard/",
              "high", "pending_auto", "guia_tecnica",
              "manual/owasp/owasp_asvs_v4_0.pdf",
              "Application Security Verification Standard",
              ["mp.sw.1"]),
]


# === GROUP 5: CCN-STIC Serie 400-500 (hardening) ============================
_CCN_HARDENING: list[CorpusDoc] = [
    CorpusDoc("CCN-STIC-599", "Guía Windows Server 2019/2022", "ccn_stic",
              "https://www.ccn-cert.cni.es/",
              "high", "pending_manual", "hardening",
              "manual/ccn/hardening/ccn_stic_599_windows_server.pdf",
              "Hardening Windows Server según CCN",
              ["mp.eq.1", "op.exp.2"]),
    CorpusDoc("CCN-STIC-617", "Guía Ubuntu LTS", "ccn_stic",
              "https://www.ccn-cert.cni.es/",
              "high", "pending_manual", "hardening",
              "manual/ccn/hardening/ccn_stic_617_ubuntu.pdf",
              "Hardening Ubuntu LTS según CCN"),
    CorpusDoc("CCN-STIC-453", "Guía Microsoft 365", "ccn_stic",
              "https://www.ccn-cert.cni.es/",
              "high", "pending_manual", "hardening",
              "manual/ccn/hardening/ccn_stic_453_m365.pdf",
              "Hardening Microsoft 365"),
    CorpusDoc("CCN-STIC-457", "Guía Azure", "ccn_stic",
              "https://www.ccn-cert.cni.es/",
              "high", "pending_manual", "hardening",
              "manual/ccn/hardening/ccn_stic_457_azure.pdf",
              "Hardening Azure"),
    CorpusDoc("CCN-STIC-887", "Guía AWS", "ccn_stic",
              "https://www.ccn-cert.cni.es/",
              "high", "pending_manual", "hardening",
              "manual/ccn/hardening/ccn_stic_887_aws.pdf",
              "Hardening AWS"),
    CorpusDoc("CCN-STIC-886", "Guía GCP", "ccn_stic",
              "https://www.ccn-cert.cni.es/",
              "medium", "pending_manual", "hardening",
              "manual/ccn/hardening/ccn_stic_886_gcp.pdf",
              "Hardening Google Cloud Platform"),
    CorpusDoc("CCN-STIC-836", "Guía Firewall perimetrales", "ccn_stic",
              "https://www.ccn-cert.cni.es/",
              "medium", "pending_manual", "hardening",
              "manual/ccn/hardening/ccn_stic_836_firewall.pdf",
              "Hardening de cortafuegos perimetrales",
              ["mp.com.1"]),
    CorpusDoc("CCN-STIC-844", "Guía WiFi", "ccn_stic",
              "https://www.ccn-cert.cni.es/",
              "medium", "pending_manual", "hardening",
              "manual/ccn/hardening/ccn_stic_844_wifi.pdf",
              "Hardening de redes inalámbricas",
              ["mp.com.2"]),
]


# === GROUP 6: MAGERIT + PCE =================================================
_MAGERIT_PCE: list[CorpusDoc] = [
    CorpusDoc("MAGERIT-L1", "MAGERIT v3 Libro I — Método", "magerit",
              "https://administracionelectronica.gob.es/pae_Home/pae_Documentacion/pae_Metodolog/pae_Magerit.html",
              "critical", "pending_manual", "metodologia",
              "manual/magerit/magerit_v3_l1_metodo.pdf",
              "Método de análisis y gestión de riesgos"),
    CorpusDoc("MAGERIT-L2", "MAGERIT v3 Libro II — Catálogo", "magerit",
              "https://administracionelectronica.gob.es/pae_Home/pae_Documentacion/pae_Metodolog/pae_Magerit.html",
              "critical", "pending_manual", "metodologia",
              "manual/magerit/magerit_v3_l2_catalogo.pdf",
              "Catálogo de elementos (activos, amenazas, salvaguardas)"),
    CorpusDoc("MAGERIT-L3", "MAGERIT v3 Libro III — Técnicas", "magerit",
              "https://administracionelectronica.gob.es/pae_Home/pae_Documentacion/pae_Metodolog/pae_Magerit.html",
              "high", "pending_manual", "metodologia",
              "manual/magerit/magerit_v3_l3_tecnicas.pdf",
              "Técnicas auxiliares (matriz de impacto, diagramas, etc.)"),
    CorpusDoc("PCE-PYME", "Perfil Cumplimiento Específico PYME",
              "pce",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
              "high", "pending_manual", "perfil_cumplimiento",
              "manual/pce/pce_pyme.pdf",
              "PCE para pequeñas y medianas empresas"),
    # PCE-AAPP-LOCAL: perfil CCN-STIC oficial · NO nombre customer (target FULKRO
    # = empresa privada licitando AAPP, AMEND-012). Aplica a sistemas privados
    # que sirven Admón Local · ref m27_conformity.service KNOWN_OVERLAYS.
    CorpusDoc("PCE-AAPP-LOCAL", "PCE AAPP Local",
              "pce",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
              "high", "pending_manual", "perfil_cumplimiento",
              "manual/pce/pce_aapp_local.pdf",
              "PCE para administración local"),
    CorpusDoc("PCE-SALUD", "PCE Sector Salud",
              "pce",
              "https://www.ccn-cert.cni.es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad",
              "high", "pending_manual", "perfil_cumplimiento",
              "manual/pce/pce_salud.pdf",
              "PCE para entidades sanitarias",
              ["mp.info.1"]),
]


# === GROUP 7: Otros =========================================================
_OTHERS: list[CorpusDoc] = [
    # Sub-lote 1.B.5.2 · ingested via ccn_pdf_ingest.py (DB code = "AEPD-RIESGO-EIPD")
    CorpusDoc("AEPD-EIPD", "Guía EIPD AEPD (gestión de riesgo + evaluación de impacto)", "aepd",
              "https://www.aepd.es/guias/gestion-riesgo-y-evaluacion-impacto-en-tratamientos-datos-personales.pdf",
              "high", "ingested", "guia_aepd",
              "manual/aepd/gestion-riesgo-y-evaluacion-impacto-en-tratamientos-datos-personales.pdf",
              "Guía oficial AEPD gestión de riesgo y evaluación de impacto en tratamientos de datos personales"),
    CorpusDoc("AEPD-BRECHAS", "Guía gestión brechas AEPD", "aepd",
              "https://www.aepd.es/guias/guia-brechas-seguridad.pdf",
              "high", "pending_manual", "guia_aepd",
              "manual/aepd/aepd_brechas.pdf",
              "Guía para gestión y notificación de brechas a la AEPD",
              ["op.exp.7"]),
    CorpusDoc("INCIBE-GUIA-PYME", "Guía ciberseguridad PYME INCIBE", "incibe",
              "https://www.incibe.es/empresas/guias",
              "medium", "pending_auto", "guia_incibe",
              "manual/incibe/incibe_pyme.pdf",
              "Guía esencial de ciberseguridad para PYME"),
    CorpusDoc("ENS-FAQ", "FAQ oficiales ENS", "ccn_stic",
              "https://ens.ccn.cni.es/es/faqs",
              "medium", "pending_manual", "guia_tecnica",
              "manual/ccn/ens_faq.html",
              "Preguntas frecuentes oficiales del ENS"),
    CorpusDoc("PILAR-MANUAL", "Manual herramienta PILAR", "magerit",
              "https://www.ccn.cni.es/index.php/es/menu-ccn-es/herramientas-de-ciberseguridad/pilar",
              "medium", "pending_manual", "manual_herramienta",
              "manual/magerit/pilar_manual.pdf",
              "Manual de la herramienta PILAR del CCN"),
    CorpusDoc("LUCIA-MANUAL", "Manual herramienta LUCIA", "ccn_stic",
              "https://www.ccn.cni.es/index.php/es/menu-ccn-es/herramientas-de-ciberseguridad/lucia",
              "medium", "pending_manual", "manual_herramienta",
              "manual/ccn/lucia_manual.pdf",
              "Manual de la herramienta de incidentes LUCIA"),
    CorpusDoc("PCI-DSS-v4", "PCI DSS v4.0 (resumen público)", "pci_dss",
              "https://www.pcisecuritystandards.org/document_library",
              "medium", "pending_manual", "estandar_internacional",
              "manual/pci/pci_dss_v4.pdf",
              "Estándar PCI-DSS v4.0 para procesamiento de tarjetas"),
    CorpusDoc("CCN-CERT-INFORMES", "Informes anuales CCN-CERT", "ccn_stic",
              "https://www.ccn-cert.cni.es/informes",
              "medium", "pending_auto", "guia_tecnica",
              "manual/ccn/ccn_cert_informes.pdf",
              "Informes anuales de ciberamenazas del CCN-CERT"),
]


CORPUS_CATALOG: list[CorpusDoc] = (
    _INGESTED + _EUR_LEX + _CCN_STIC_800 + _BOE_EXTRA
    + _STANDARDS + _CCN_HARDENING + _MAGERIT_PCE + _OTHERS
)


def list_documents(
    status: Status | None = None,
    priority: Priority | None = None,
    source_type: SourceType | None = None,
) -> list[CorpusDoc]:
    """Filter the catalog by status / priority / source_type."""
    out = list(CORPUS_CATALOG)
    if status is not None:
        out = [d for d in out if d.status == status]
    if priority is not None:
        out = [d for d in out if d.priority == priority]
    if source_type is not None:
        out = [d for d in out if d.source_type == source_type]
    return out


def get_document(source_id: str) -> CorpusDoc | None:
    for d in CORPUS_CATALOG:
        if d.source_id == source_id:
            return d
    return None


def by_priority() -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in CORPUS_CATALOG:
        counts[d.priority] = counts.get(d.priority, 0) + 1
    return counts


def by_status() -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in CORPUS_CATALOG:
        counts[d.status] = counts.get(d.status, 0) + 1
    return counts
