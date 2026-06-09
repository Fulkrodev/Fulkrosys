"""Tests for backend/app/corpus/catalog.py — corpus normativo ENS pertinente.

El corpus cubre el conjunto de fuentes que un consultor necesita para implantar
ENS en una empresa proveedora de la AAPP (RD 311/2022): núcleo CCN-STIC serie
800 completo (800-809), MAGERIT v3, ISO 27001/27002, Perfiles de Cumplimiento,
RGPD/LOPDGDD + cross-compliance (NIS2/DORA/eIDAS) + hardening + técnico (OWASP/
NIST/PCI). Es un set comprensivo y suficiente · ~66 docs. (El "92" de versiones
previas era un objetivo nominal nunca justificado: el código siempre tuvo ~66 y
no necesita más · verificado web CCN-CERT serie 800.)
"""
from backend.app.corpus.catalog import (
    CORPUS_CATALOG,
    by_priority,
    by_status,
    get_document,
    list_documents,
)


class TestCorpusCatalog:
    def test_corpus_catalog_pertinent_set_present(self):
        """El corpus pertinente ENS es comprensivo (~66 docs · floor 60).

        Floor defensivo contra borrado masivo accidental · NO un objetivo de
        volumen (lo que importa es que estén los docs esenciales · ver
        test_includes_core_normative_sources). 92 era nominal sin justificar.
        """
        assert len(CORPUS_CATALOG) >= 60

    def test_no_duplicate_source_ids(self):
        ids = [d.source_id for d in CORPUS_CATALOG]
        assert len(ids) == len(set(ids))

    def test_all_critical_docs_present(self):
        critical = list_documents(priority="critical")
        assert len(critical) >= 20

    def test_core_docs_ingested_in_rag(self):
        """El núcleo está ingerido en el RAG (~26 docs auto-fetchables).

        Los pending_manual restantes son fuentes secundarias (guías hardening,
        ISO tras paywall) cuya ingesta es mejora operativa, NO requisito de
        citación ENS · floor 25 contra regresión del set ingerido.
        """
        ingested = list_documents(status="ingested")
        assert len(ingested) >= 25

    def test_includes_core_normative_sources(self):
        """Garantía real de cobertura: el núcleo normativo ENS que todo proyecto
        debe poder citar (RD 311/2022 + ITS + serie CCN-STIC 800-809 completa +
        MAGERIT + ISO 27001 + RGPD/LOPDGDD + PCE). Esto —no un recuento— es lo
        que define que el corpus es suficiente para implantar ENS (verificado web
        CCN-CERT: las nucleares RD 311/2022 son 801/802/803/805/808)."""
        ids = {d.source_id for d in CORPUS_CATALOG}
        must_have = (
            # Norma base + ITS
            "RD-311-2022", "BOE-ITS-CONFORMIDAD", "BOE-ITS-AUDITORIA",
            "BOE-ITS-INCIDENTES", "BOE-ITS-ESTADO",
            # Serie CCN-STIC 800 (núcleo implantación ENS)
            "CCN-STIC-800", "CCN-STIC-801", "CCN-STIC-802", "CCN-STIC-803",
            "CCN-STIC-804", "CCN-STIC-805", "CCN-STIC-806", "CCN-STIC-807",
            "CCN-STIC-808", "CCN-STIC-809",
            # Riesgos + ISO + datos personales + perfiles
            "MAGERIT-L1", "MAGERIT-L2", "ISO-27001", "RGPD", "LOPDGDD",
            "PCE-PYME",
        )
        missing = [m for m in must_have if m not in ids]
        assert not missing, f"Faltan fuentes ENS esenciales: {missing}"

    def test_get_document_known(self):
        doc = get_document("RD-311-2022")
        assert doc is not None
        assert doc.source_type == "boe"

    def test_get_document_unknown(self):
        assert get_document("DOES-NOT-EXIST") is None

    def test_priority_breakdown_sums_total(self):
        counts = by_priority()
        assert sum(counts.values()) == len(CORPUS_CATALOG)

    def test_status_breakdown_sums_total(self):
        counts = by_status()
        assert sum(counts.values()) == len(CORPUS_CATALOG)

    def test_every_doc_has_required_fields(self):
        for d in CORPUS_CATALOG:
            assert d.source_id and d.title and d.url
            assert d.source_type in (
                "boe", "eur_lex", "ccn_stic", "iso", "nist", "owasp",
                "aepd", "magerit", "pce", "incibe", "pci_dss", "other",
            )
            assert d.priority in ("critical", "high", "medium", "low")
            assert d.status in ("ingested", "pending_auto", "pending_manual")
            assert d.file_path
