"""Lo que el sistema emite y firma llega al expediente del auditor.

LA REGLA
    ``documents`` es la tabla que lee ``dossier_generator._collect_documents``.
    Lo que no está ahí, para el auditor no existe. Tres documentos firmables
    salían fuera de ese registro, cada uno por un motivo distinto:

    1. **E-604, adenda de proveedor.** Se renderizaba por su cuenta con
       ``render_docx``, se subía a MinIO y se anotaba en ``provider_addendums``.
       Tenía plantilla en el catálogo, así que era enchufable tal cual: ahora
       sale por la fábrica documental, que calcula la huella, firma, registra y
       sube copia durable.

    2. **E-005, acta de comité.** Se construye con ``python-docx`` desde datos
       estructurados, no desde plantilla Jinja ("E-005 sin plantilla" consta en
       tres sitios de m09), así que no se puede meter en la fábrica sin crear
       antes la plantilla. Pero eso no era lo que impedía que el auditor la
       viera: lo que faltaba era la fila. Se registra con la MISMA huella y la
       MISMA firma Ed25519 que el servicio ya calculaba.

    3. **Informe INES del art. 32.** Es anual y POR ORGANIZACIÓN, y
       ``documents`` exigía ``project_id NOT NULL``. Registrarlo obligaba a
       inventarse a qué proyecto pertenece el informe de una organización con
       varios. La migración ``ines_cabe_documents_001`` abre el ámbito de
       organización (``project_id`` nullable + ``client_id`` + CHECK de que haya
       al menos uno) con la política RLS de dos ramas que este repositorio ya
       usa en ``audit_log``.
"""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]


def test_la_adenda_e604_sale_por_la_fabrica():
    fuente = (RAIZ / "backend" / "app" / "motors" / "m14_contracts"
              / "adenda_generator.py").read_text(encoding="utf-8")
    assert "DocumentFactoryService" in fuente, (
        "la adenda E-604 vuelve a renderizarse por su cuenta: no dejará fila en "
        "`documents` y no llegará al expediente"
    )
    assert "render_docx(TEMPLATE_DOCX_PATH" not in fuente


def test_el_acta_e005_deja_fila_en_documents():
    fuente = (RAIZ / "backend" / "app" / "motors" / "m18_communication"
              / "minutes_service.py").read_text(encoding="utf-8")
    assert "_registrar_en_documents" in fuente, (
        "el acta E-005 vuelve a quedarse sólo en `meetings`"
    )
    # Y con la huella y la firma que ya existían, no con otras inventadas.
    assert "fila.rendered_hash = m.hash_sha256" in fuente
    assert "fila.signature_ed25519 = m.signature_ed25519" in fuente


def test_documents_admite_el_ambito_de_organizacion():
    from backend.app.models.documents import Document

    assert Document.__table__.c.project_id.nullable, (
        "`documents.project_id` vuelve a ser NOT NULL: el informe INES del "
        "art. 32, que es por organización y no por proyecto, se queda otra vez "
        "fuera del inventario documental"
    )
    assert "client_id" in Document.__table__.c, (
        "falta el ámbito de organización en `documents`"
    )


def test_el_informe_ines_se_registra():
    fuente = (RAIZ / "backend" / "app" / "motors" / "m27_conformity"
              / "api.py").read_text(encoding="utf-8")
    assert "_registrar_ines_en_documents" in fuente, (
        "el informe INES vuelve a entregarse sin dejar rastro en `documents`"
    )


def test_la_migracion_exige_que_todo_documento_tenga_ambito():
    """Nullable no puede significar 'sin ámbito': el CHECK lo impide."""
    migracion = (RAIZ / "backend" / "migrations" / "versions"
                 / "ines_cabe_en_documents_001.py").read_text(encoding="utf-8")
    assert "ck_documents_ambito" in migracion
    assert "project_id IS NOT NULL OR client_id IS NOT NULL" in migracion


def test_el_best_effort_del_ines_revierte_antes_de_devolver():
    """Capturar sin revertir deja la promesa escrita y sin cumplir.

    ``_registrar_ines_en_documents`` promete en su docstring que, si el registro
    falla, «el informe se entrega igual». Eso sólo es cierto si además se
    REVIERTE: en PostgreSQL un statement fallido aborta la transacción entera y
    SQLAlchemy la marca para rollback, así que el ``await db.commit()`` que
    viene detrás revienta con ``PendingRollbackError`` y el endpoint devuelve
    500 — justo lo que el ``except`` dice estar evitando.

    Comprobado con una sesión de mentira que falla al leer: lo que se exige es
    que llame a ``rollback()``.
    """
    import asyncio
    import uuid

    from backend.app.motors.m27_conformity.api import _registrar_ines_en_documents

    class SesionQueFalla:
        def __init__(self):
            self.rollbacks = 0

        async def execute(self, *a, **k):
            raise RuntimeError("la lectura de `documents` falla")

        async def rollback(self):
            self.rollbacks += 1

        def add(self, _obj):  # pragma: no cover — no se llega
            raise AssertionError("no debería llegar a añadir nada")

        async def flush(self):  # pragma: no cover — no se llega
            raise AssertionError("no debería llegar a hacer flush")

    db = SesionQueFalla()
    asyncio.run(_registrar_ines_en_documents(db, uuid.uuid4(), 2026, b"x"))

    assert db.rollbacks == 1, (
        "el registro del INES falló y no se revirtió: el `await db.commit()` "
        "del endpoint reventará con PendingRollbackError y el informe NO se "
        "entregará, pese a que el except promete que sí"
    )
