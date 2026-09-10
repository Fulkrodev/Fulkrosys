#!/usr/bin/env python3
"""Cataloga los identificadores REALES que necesitan las 83 rutas dinamicas.

Por que existe: `frontend/app` declara 167 paginas y 83 de ellas llevan un
parametro en la ruta (`[id]`, `[token]`, `[tipo]`, `[norma_key]`). Recorrerlas
exige valores que EXISTAN en la base del demo. Inventarse un UUID y visitar la
ruta produce una pagina de error que carga con HTTP 200: exactamente la clase de
verdad vacia que esta campanya existe para no repetir.

Este script NO inventa nada. Lee la base y, para los portales por token, ACUNYA
enlaces de verdad con el mismo servicio que usa la aplicacion
(`MagicLinkService`), asi que el token y su codigo de un solo uso son los que
recibiria una persona real.

Lo que NO puede resolver lo devuelve en `sin_dato`, con el motivo escrito. El
arnes marca esas rutas NO VERIFICADA y jamas las cuenta como aprobadas.

Uso (dentro del contenedor del backend):
    docker cp scripts/recorrido_identificadores.py fulkro-demo-backend-1:/tmp/ && \
    docker exec -e PYTHONPATH=/app fulkro-demo-backend-1 python /tmp/recorrido_identificadores.py

Salida: JSON por stdout.
"""
from __future__ import annotations

import asyncio
import json
import sys
import uuid

from sqlalchemy import select, text

from backend.app.database import async_session
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService

# Cada portal por token de `frontend/app` y el proposito de magic-link que lo
# abre. Se dedujo leyendo la propia pagina (no de la documentacion).
# Lo que tiene que EXISTIR en la base para que cada portal pueda ensenyar algo.
# Sin esto, el arnes contaba como FALLO que el portal del pentester dijera
# "Handoff not found", cuando lo que pasa es que el demo no siembra ningun
# encargo de pentest. La tabla se comprueba antes de acunyar el enlace.
REQUISITO_POR_PORTAL = {
    "pentester-portal": (
        "external_pentester_handoffs",
        "el demo no crea ningun encargo a pentester externo",
    ),
    "verify-auth": (
        "verification_runs",
        "el demo no crea ninguna verificacion tecnica que autorizar",
    ),
    "diagnostico": (
        "diagnosis_runs",
        "el demo no crea ninguna sesion de diagnostico previo",
    ),
}

PORTALES_POR_TOKEN = {
    "auditor-portal": MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
    "diagnostico": MagicLinkPurpose.DIAGNOSTICO_PRECLIENTE,
    "pentester-portal": MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO,
    "remediation": MagicLinkPurpose.PORTAL_REMEDIACION,
    "verify-auth": MagicLinkPurpose.AUTORIZAR_VERIFICACION_TECNICA,
    "sign": MagicLinkPurpose.FIRMA_DOCUMENTO,
    "download": MagicLinkPurpose.DESCARGA_DOSSIER_FINAL,
}


async def _uno(db, sql: str):
    """Primera columna de la primera fila, o None si no hay filas."""
    try:
        return (await db.execute(text(sql))).scalar_one_or_none()
    except Exception as exc:  # noqa: BLE001
        # Se avisa por stderr: un fallo de consulta que devuelve None en
        # silencio se confundiria con "no hay dato", que es justo la mentira
        # que este catalogo existe para no contar.
        print(f"AVISO: consulta fallida ({type(exc).__name__}: {exc})",
              file=sys.stderr)
        return None


async def _sembrar_huecos(db, catalogo: dict) -> None:
    """Crea, POR LA VIA DE SERVICIO DE LA PROPIA APLICACION, las entidades que
    el sembrado del demo NO cubre.

    Es un HALLAZGO, no un apanyo: `make demo` deja tres familias de rutas sin un
    solo dato con el que poder recorrerlas (`/admin/meetings/[id]`,
    `/admin/pipeline/leads/[id]` y
    `/admin/compliance/norma-reports/[norma_key]`). Se siembra aqui para poder
    VERIFICARLAS, y el informe dice explicitamente que el dato lo puso el arnes
    y no el demo. Callarlo convertiria un hueco del sembrado en un aprobado.

    Se usan los mismos servicios que usan los endpoints (MeetingService,
    NormaReportsService), no INSERTs a mano: si el servicio se rompe, esto se
    rompe, que es lo que se quiere.
    """
    proyecto = catalogo["ids"].get("project_id")
    cliente = catalogo["ids"].get("client_id")

    # ── reunion de comite ──────────────────────────────────────────────────
    if "meeting_id" not in catalogo["ids"] and cliente:
        try:
            from backend.app.motors.m_meetings.schemas import MeetingCreate
            from backend.app.motors.m_meetings.service import MeetingService

            svc = MeetingService(db)
            reunion = await svc.create_meeting(
                MeetingCreate(
                    client_id=uuid.UUID(cliente),
                    project_id=uuid.UUID(proyecto) if proyecto else None,
                    title="Reunion de seguimiento (sembrada por el recorrido)",
                )
            )
            await db.flush()
            catalogo["ids"]["meeting_id"] = str(reunion.id)
            catalogo["sembrado_por_el_arnes"]["meeting_id"] = (
                "MeetingService.create_meeting · el sembrado del demo no crea "
                "ninguna reunion"
            )
            catalogo["sin_dato"].pop("meeting_id", None)
        except Exception as exc:  # noqa: BLE001
            catalogo["sin_dato"]["meeting_id"] = (
                f"la tabla esta vacia y sembrarla fallo: {type(exc).__name__}: {exc}"
            )

    # ── lead comercial ─────────────────────────────────────────────────────
    # Por LeadService, NO por `/api/v1/_dev/seed-commercial-lead`: ese endpoint
    # ademas RENOMBRA al cliente del demo (ver la guarda que se le puso el
    # 2026-09-10 en backend/app/dev/router.py). Aqui solo hace falta un lead.
    if "lead_id" not in catalogo["ids"]:
        try:
            from backend.app.motors.m13_commercial.services.lead_service import (
                LeadService,
            )

            lead = await LeadService(db).create_lead(
                empresa_nombre="Innovacion Digital del Guadalquivir, S.L.",
                contacto_email="lucia.ramirez@idguadalquivir.example",
                empresa_cif="B99999999",
                sector="Servicios tecnologicos · SaaS para la AAPP",
                origen="manual",
                asignado_a="Marcos",
                categoria_objetivo_ens="MEDIA",
                estado_contacto="nuevo",
                notas="Lead sembrado por el recorrido completo (BLOQUE E).",
            )
            await db.flush()
            catalogo["ids"]["lead_id"] = str(lead.id)
            catalogo["sembrado_por_el_arnes"]["lead_id"] = (
                "LeadService.create_lead · el sembrado del demo no crea ningun lead"
            )
            catalogo["sin_dato"].pop("lead_id", None)
        except Exception as exc:  # noqa: BLE001
            catalogo["sin_dato"]["lead_id"] = (
                f"la tabla esta vacia y sembrarla fallo: {type(exc).__name__}: {exc}"
            )

    # ── informe de norma ───────────────────────────────────────────────────
    if "norma_key" not in catalogo["ids"]:
        try:
            from backend.app.motors.m_compliance_monitor.norma_reports_service import (
                ComplianceNormaReportsService,
            )

            informes = await ComplianceNormaReportsService(db).generate_all_due()
            await db.flush()
            if informes:
                catalogo["ids"]["norma_key"] = informes[0].norma_key
                catalogo["sembrado_por_el_arnes"]["norma_key"] = (
                    f"ComplianceNormaReportsService.generate_all_due · genero "
                    f"{len(informes)} informes; el sembrado del demo no genera "
                    f"ninguno"
                )
                catalogo["sin_dato"].pop("norma_key", None)
            else:
                catalogo["sin_dato"]["norma_key"] = (
                    "generate_all_due() no devolvio ningun informe"
                )
        except Exception as exc:  # noqa: BLE001
            catalogo["sin_dato"]["norma_key"] = (
                f"la tabla esta vacia y generarla fallo: {type(exc).__name__}: {exc}"
            )


async def main() -> None:
    catalogo: dict = {
        "ids": {}, "tokens": {}, "sin_dato": {},
        "sembrado_por_el_arnes": {},
    }

    async with async_session() as db:
        # El recorrido es de solo lectura salvo el acunyado de enlaces; se
        # necesita ver todas las filas de todos los clientes.
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

        # ── proyecto y cliente del demo ────────────────────────────────────
        # USAGE.md dice que el unico proyecto CON DATOS es el de NovaEdge.
        # Recorrer las 60+ subpaginas de proyecto contra un proyecto vacio
        # mediria el vacio, no la aplicacion.
        proyecto = await _uno(db, """
            SELECT p.id::text FROM projects p JOIN clients c ON c.id = p.client_id
            WHERE c.nombre ILIKE 'NovaEdge%' LIMIT 1
        """)
        cliente = await _uno(db, """
            SELECT id::text FROM clients WHERE nombre ILIKE 'NovaEdge%' LIMIT 1
        """)
        catalogo["ids"]["project_id"] = proyecto
        catalogo["ids"]["client_id"] = cliente

        # Los demas proyectos, para poder decir cuales estan vacios a proposito.
        filas = (await db.execute(text("""
            SELECT p.id::text, c.nombre FROM projects p
            JOIN clients c ON c.id = p.client_id ORDER BY c.nombre
        """))).all()
        catalogo["ids"]["todos_los_proyectos"] = [
            {"id": f[0], "cliente": f[1]} for f in filas
        ]

        # ── el resto de entidades con ruta propia ──────────────────────────
        # Cada una con la tabla que la respalda, medida, no supuesta.
        entidades = {
            "meeting_id": ("committee_meetings", "SELECT id::text FROM committee_meetings LIMIT 1"),
            "lead_id": ("leads", "SELECT id::text FROM leads LIMIT 1"),
            "magerit_analysis_id": ("magerit_analysis", "SELECT id::text FROM magerit_analysis LIMIT 1"),
            "norma_key": ("fulkro_compliance_norma_reports",
                          "SELECT norma_key FROM fulkro_compliance_norma_reports LIMIT 1"),
            "registro_tipo": ("live_records", None),
        }
        for clave, (tabla, sql) in entidades.items():
            if sql is None:
                continue
            valor = await _uno(db, sql)
            if valor:
                catalogo["ids"][clave] = valor
            else:
                catalogo["sin_dato"][clave] = (
                    f"la tabla `{tabla}` esta vacia en el demo sembrado"
                )

        # `registros/[tipo]` no lleva un id de fila: lleva el CODIGO del registro
        # vivo, un catalogo cerrado que declara el frontend en
        # `frontend/lib/types/live-records.ts` (E-300 .. E-325).
        #
        # El primer intento puso aqui "incidentes", que sonaba razonable y era
        # falso: la pagina devolvia «404 Pagina no encontrada». Sirve de aviso
        # sobre este catalogo entero — un identificador PLAUSIBLE no es un
        # identificador REAL, y la unica diferencia visible entre los dos es que
        # el segundo trae datos en pantalla.
        catalogo["ids"]["registro_tipo"] = "E-300"

        await _sembrar_huecos(db, catalogo)

        # ── portales por token: se acunyan enlaces DE VERDAD ───────────────
        # El rol elevado se vuelve a pedir aqui a proposito: `SET LOCAL ROLE`
        # dura lo que dure la TRANSACCION, y los servicios que acaban de sembrar
        # pueden haberla cerrado. Sin esto, el INSERT en `magic_links` lo tumba
        # la propia RLS de la tabla, que es exactamente lo que debe hacer.
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        if proyecto:
            svc = MagicLinkService(db)
            for portal, purpose in PORTALES_POR_TOKEN.items():
                # Un enlace VALIDO a un portal SIN entidad detras no verifica
                # nada: la pagina abre y dice, correctamente, "no se pudo cargar
                # el engagement" o "el enlace no tiene session_id en scope". Eso
                # NO es un defecto de la aplicacion —es la aplicacion diciendo la
                # verdad— y contarlo como fallo seria culpar al sujeto de un
                # hueco del sembrado. Se declara NO VERIFICADA, que es su sitio.
                requisito = REQUISITO_POR_PORTAL.get(portal)
                if requisito:
                    tabla, descripcion = requisito
                    n = await _uno(db, f"SELECT count(*) FROM {tabla}")
                    if not n:
                        catalogo["sin_dato"][f"token:{portal}"] = (
                            f"el enlace se puede acunyar, pero la tabla "
                            f"`{tabla}` esta vacia: {descripcion}"
                        )
                        continue
                try:
                    res = await svc.generate_magic_link(
                        MagicLinkGenerateRequest(
                            project_id=uuid.UUID(proyecto),
                            purpose=purpose,
                            recipient_email=f"recorrido.{portal}@test.fulkro.es",
                        ),
                        base_url="http://localhost",
                    )
                    catalogo["tokens"][portal] = {
                        "token": res.token,
                        "otp": res.otp,
                        "purpose": purpose.value,
                    }
                except Exception as exc:  # noqa: BLE001
                    catalogo["sin_dato"][f"token:{portal}"] = (
                        f"no se pudo acunyar un enlace {purpose.value}: "
                        f"{type(exc).__name__}: {exc}"
                    )
            await db.commit()
        else:
            catalogo["sin_dato"]["project_id"] = "no hay ningun proyecto en la base"

    # SQLAlchemy echo ensucia stdout: el JSON va a un fichero y por stdout solo
    # sale su ruta, para que quien lo invoca no tenga que adivinar donde acaba
    # el log y empieza el dato.
    destino = sys.argv[1] if len(sys.argv) > 1 else "/tmp/identificadores.json"
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(catalogo, fh, ensure_ascii=False, indent=2)
    print(f"CATALOGO_ESCRITO_EN={destino}")


if __name__ == "__main__":
    asyncio.run(main())
