"""Servicio común de provisión de proyecto (#7 · Fase 7.2).

FUENTE ÚNICA de "cómo se crea un proyecto". Extraído **verbatim** del wizard
admin (``admin_diagnostico_wizard.create_project_with_diagnosis``) para que el
wizard manual Y la auto-conversión por firma (#7.4) NO diverjan (hoy divergían:
el wizard creaba el stack completo y la conversión un Project fino).

REFACTOR DE EQUIVALENCIA (#7.2): el cuerpo es el del wizard, SIN cambios de
comportamiento. ``test_admin_diagnostico_wizard.py`` prueba la equivalencia.

Los steps ``s1..s5`` se reciben **duck-typed** (el caller pasa los schemas
Pydantic del wizard; el servicio solo lee atributos) → el servicio NO importa
los schemas del API (sin ciclo).
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import set_tenant_context
from backend.app.models.core import Client, Project

logger = logging.getLogger(__name__)

# Mapeos hardcoded movidos verbatim desde el wizard (equivalencia).
_TAMANO_TO_EMPLEADOS = {
    "micro": 5, "pequeno": 25, "mediano": 125, "grande": 500, "enterprise": 2000,
}
_ASSET_TYPE_MAP = {
    "datos": "[D]", "servicios": "[S]", "infraestructura": "[HW]",
    "software": "[SW]", "personal": "[P]",
}
_ARCHETYPE_MAP = {
    ("aapp", "sector_publico"): "aapp_local",
    ("privado_licita_aapp", "pyme"): "privado_licita_aapp",
    ("privado_licita_aapp", "gran_empresa"): "privado_licita_aapp",
    ("privado_proveedor_aapp", "pyme"): "privado_proveedor",
}


def _impact_to_valoracion(impact: str) -> str:
    return impact


async def resolve_lead_client_id(db: AsyncSession, lead: Any) -> uuid.UUID | None:
    """#7.5 · Localiza el client_id del proyecto LIGERO de un lead por señales
    NO-RLS del propio lead (su CIF · su email). ``clients`` no tiene RLS, así que
    es legible sin contexto; ``projects`` SÍ → hay que fijar el contexto de ESTE
    cliente antes de poder leer su proyecto. Usar el CIF/email del LEAD (no el del
    wizard, que el admin podría cambiar) cubre el caso del lead sin CIF
    formalizado (cliente ligero con CIF placeholder · mismo email)."""
    # ``cif = NULL`` / ``contacto_email = NULL`` ya evalúan a falso, así que no
    # hace falta el guard IS NOT NULL (que además rompe la inferencia de tipos de
    # asyncpg con el bind aislado · AmbiguousParameterError).
    return (await db.execute(text(
        "SELECT id FROM clients WHERE cif = :lcif OR contacto_email = :lemail "
        "LIMIT 1"
    ), {"lcif": lead.empresa_cif, "lemail": lead.contacto_email})).scalar_one_or_none()


async def emit_conversion_audit_log(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    client_id: uuid.UUID,
    lead_id: uuid.UUID,
    source: str,
    user: str = "system",
) -> None:
    """#7.6 · audit_log R6 de la conversión lead→proyecto. El hash chain lo
    calcula el trigger (migración d4f8b2a90001) → inmutable. Sub-atom 5.A 3-way
    OR (project_id + client_id propagados). ``source`` ∈ {'firma', 'wizard'}.
    El contexto de tenant debe estar fijado por el caller (project_id/client_id)."""
    await db.execute(text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, client_id, payload_new, timestamp) "
        "VALUES (gen_random_uuid(), 'projects', :pid, "
        "'lead.converted_to_project', :user, :pid, :cid, :payload, now())"
    ), {
        "pid": str(project_id),
        "cid": str(client_id),
        "user": user[:255],
        "payload": json.dumps({"lead_id": str(lead_id), "source": source}),
    })


@dataclass(slots=True)
class ProvisionResult:
    """IDs + contadores producidos por ``provision_project`` (para que el
    caller construya su response)."""

    client_id: uuid.UUID
    project_id: uuid.UUID
    magerit_analysis_id: uuid.UUID | None
    initial_system_id: uuid.UUID
    initial_information_type_id: uuid.UUID
    cockpit_user_id: uuid.UUID | None
    departments_created_count: int
    magic_link_sent: bool
    dims_captured_count: int
    summary: str


async def provision_project(
    db: AsyncSession,
    *,
    s1: Any,  # StepDatosCliente
    s2: Any,  # StepContextoENS
    s3: Any,  # StepCategoriaPreliminar
    s4: Any,  # StepActivosCriticos
    s5: Any,  # StepFirstUser
    lead_id: uuid.UUID | None = None,  # #7.5 hidratación desde lead
) -> ProvisionResult:
    """Crea Client+Project+dims+m01+m30+m02+ClientUser en 1 transacción.

    Movido verbatim desde el wizard atomic (equivalencia probada por sus tests).

    #7.5 · ``lead_id`` opcional: si el lead ya tiene un PROYECTO LIGERO
    (DRAFT/pre_venta · #7.3) se REUSA/PROMUEVE ese mismo proyecto (no duplica ·
    decisión 2-A · mantiene la invariante "un proyecto por lead" de #7.4); si no,
    se crea fresco y se enlaza ``convertido_a_proyecto_id``. Con ``lead_id=None``
    el comportamiento es IDÉNTICO al wizard original (equivalencia #7.2 intacta).
    """
    # ─── 0) Lead + lock + resolución del PROYECTO LIGERO (#7.5 · 2-A) ───
    # La fuente AUTORITATIVA del reuse es ``lead.convertido_a_proyecto_id`` (no el
    # CIF del wizard). ``projects`` tiene RLS por cliente → para leer ese proyecto
    # hay que fijar el contexto de SU cliente, que localizamos por señales NO-RLS
    # del propio lead (su CIF · su email) vía ``resolve_lead_client_id``.
    lead = None
    reuse_project: Project | None = None
    reuse_client: Client | None = None
    if lead_id is not None:
        from backend.app.models.commercial import Lead
        # Pattern #22 · serializa wizard-manual vs auto-conversión por firma
        # (#7.4 · mismo servicio) sobre el MISMO lead → evita doble provisión.
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext('provision_lead_' || :lid))"),
            {"lid": str(lead_id)},
        )
        lead = await db.get(Lead, lead_id)
        if lead is not None and lead.convertido_a_proyecto_id is not None:
            light_client_id = await resolve_lead_client_id(db, lead)
            if light_client_id is not None:
                await set_tenant_context(db, client_id=light_client_id)
                candidate = await db.get(Project, lead.convertido_a_proyecto_id)
                if (
                    candidate is not None
                    and candidate.client_id == light_client_id
                    and candidate.lifecycle_state == "DRAFT"
                    and candidate.fase == "pre_venta"
                ):
                    reuse_project = candidate
                    reuse_client = await db.get(Client, light_client_id)

    # ─── 1) CLIENT (reusa el del proyecto ligero · o crea con dedup CIF) ──
    if reuse_project is not None:
        # Reusa el cliente ligero · el wizard es la autoridad de captura (incl.
        # promover un CIF placeholder al CIF real introducido en el wizard).
        client = reuse_client
        numero_empleados_estimate = _TAMANO_TO_EMPLEADOS[s2.tamano_empleados]
        client.cif = s1.cif
        client.nombre = s1.razon_social
        client.sector = s1.sector_industrial
        client.domicilio_fiscal = getattr(s1, "domicilio_fiscal", None)
        client.web = getattr(s1, "web", None)
        client.persona_contacto = getattr(s1, "persona_contacto", None)
        if s1.contacto_email:
            client.contacto_email = str(s1.contacto_email)
        if s1.contacto_telefono:
            client.contacto_telefono = s1.contacto_telefono
        client.numero_empleados = numero_empleados_estimate
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"El CIF {s1.cif} ya pertenece a otro cliente",
            )
    else:
        # Dedup por el CIF del wizard (clients sin RLS). Si ya existe → 409
        # (admin resuelve · NO re-provisiona un real ni duplica estructura hija).
        existing_client_id = (await db.execute(
            text("SELECT id FROM clients WHERE cif = :cif"),
            {"cif": s1.cif},
        )).scalar_one_or_none()
        if existing_client_id is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe un cliente con CIF {s1.cif}",
            )
        numero_empleados_estimate = _TAMANO_TO_EMPLEADOS[s2.tamano_empleados]
        client = Client(
            nombre=s1.razon_social,
            cif=s1.cif,
            sector=s1.sector_industrial,
            # #7.5 · persistir los 3 campos que antes se tiraban.
            domicilio_fiscal=getattr(s1, "domicilio_fiscal", None),
            web=getattr(s1, "web", None),
            persona_contacto=getattr(s1, "persona_contacto", None),
            contacto_email=str(s1.contacto_email) if s1.contacto_email else None,
            contacto_telefono=s1.contacto_telefono,
            numero_empleados=numero_empleados_estimate,
        )
        db.add(client)
        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Error creando cliente: {exc.orig}",
            )

    # ─── 2) PROJECT (promueve el ligero · o crea fresco) ───────────────
    await set_tenant_context(db, client_id=client.id)
    project_nombre = f"Implantación ENS · {s1.razon_social}"
    archetype = _ARCHETYPE_MAP.get((s2.sector_ens, s2.tipo_organizacion), "generico")
    # #5 (Sub-bloque E) · suelo AAPP capturado en el wizard (Paso 3). Variante 2:
    # eleva el target categoria_objetivo (solo SUBE, nunca baja) y persiste el
    # piso DURO que luego consume compute_for_system. En creación es seguro
    # (los artefactos downstream aún no existen).
    from backend.app.motors.m01_categorization.service import elevate_to_floor
    floor_aapp = getattr(s3, "categoria_heredada_aapp", None)
    categoria_target = elevate_to_floor(s3.categoria_preliminar, floor_aapp)

    if reuse_project is not None:
        project = reuse_project
        # Contexto de proyecto ANTES de mutar: el cambio de ``fase`` dispara el
        # trigger que inserta en project_lifecycle_events (RLS por project_id).
        await set_tenant_context(db, client_id=client.id, project_id=project.id)
        project.nombre = project_nombre
        project.categoria_objetivo = categoria_target
        project.categoria_heredada_aapp = floor_aapp
        project.archetype = archetype
        project.fase = "onboarding"  # sale del estado ligero (pre_venta)
        if lead is not None and lead.papel_aapp:
            project.papel_aapp = lead.papel_aapp
        await db.flush()
    else:
        project = Project(
            client_id=client.id,
            nombre=project_nombre,
            categoria_objetivo=categoria_target,
            categoria_heredada_aapp=floor_aapp,
            archetype=archetype,
            fase="onboarding",
        )
        if lead is not None and lead.papel_aapp:
            project.papel_aapp = lead.papel_aapp
        db.add(project)
        await db.flush()
    await set_tenant_context(db, client_id=client.id, project_id=project.id)

    # ─── 3) PROJECT DIMENSIONS (16 dims · Anexo L) ─────────────────────
    from backend.app.motors.m01_categorization.dimensions_service import (  # noqa: F401
        DimensionsService,
    )
    from backend.app.motors.m01_categorization.dimensions_schemas import (
        ProjectDimensionsUpdate,
    )

    dims_payload = ProjectDimensionsUpdate.model_validate({
        "tamano_empleados": s2.tamano_empleados,
        "geografia_operacion": s2.geografia_operacion,
        "arquitectura_sistemas": s2.arquitectura_sistemas,
        "equipo_ti_tamano": s2.equipo_ti_tamano,
        "dpo_designado": s2.dpo_designado,
    })
    # Patch directo sobre el ORM Project (evita el commit interno de
    # DimensionsService.update_dimensions · atomic-transaction estricta).
    for field, value in dims_payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.flush()

    # ─── 4) M01 SYSTEM + InformationType (5 ENS dims Anexo I) ──────────
    from backend.app.models.core import InformationType, System

    initial_system = System(
        project_id=project.id,
        nombre="Sistema principal",
        descripcion=(
            f"Sistema inicial seed wizard diagnóstico · {s1.razon_social}. "
            "Marcos puede crear sistemas adicionales en /admin/projects/"
            f"{project.id}/dimensiones o vía API M01."
        ),
        frontera="Implantación inicial · alcance completo SGSI",
    )
    db.add(initial_system)
    await db.flush()

    info_type = InformationType(
        system_id=initial_system.id,
        nombre="Información principal",
        valoracion_c=_impact_to_valoracion(s3.dims_anexo_i.confidencialidad),
        valoracion_i=_impact_to_valoracion(s3.dims_anexo_i.integridad),
        valoracion_d=_impact_to_valoracion(s3.dims_anexo_i.disponibilidad),
        valoracion_a=_impact_to_valoracion(s3.dims_anexo_i.autenticidad),
        valoracion_t=_impact_to_valoracion(s3.dims_anexo_i.trazabilidad),
        justificacion=s3.justificacion,
    )
    db.add(info_type)
    await db.flush()

    # ─── 5) DEPARTMENTS bulk-create (m30 1.C.F existing) ───────────────
    from backend.app.motors.m30_client_contacts.department_service import (
        DepartmentService,
        suggest_departments_for_category,
    )
    from backend.app.motors.m30_client_contacts.department_schemas import (
        DepartmentCreate,
    )

    suggestions = suggest_departments_for_category(s3.categoria_preliminar)
    dept_payloads: list[DepartmentCreate] = []
    for s in suggestions:
        dept_payloads.append(DepartmentCreate(
            code=s.code,
            name=s.name,
            description=s.description,
        ))
    dept_service = DepartmentService(db)
    departments_created = await dept_service.bulk_create(
        project.id, dept_payloads,
    )

    # ─── 6) M02 MAGERIT initial analysis + activos (Step 4) ────────────
    magerit_analysis_id: uuid.UUID | None = None
    if s4.activos:
        from backend.app.motors.m02_magerit.service import MageritService

        magerit = MageritService(db)
        analysis = await magerit.create_analysis(
            project_id=project.id,
            name="Análisis inicial · seed wizard",
            calculation_mode="qualitative",
        )
        magerit_analysis_id = analysis.id
        assets_payload = [
            {
                "code": f"ACT-{i+1:03d}",
                "name": activo.nombre,
                "asset_type_code": _ASSET_TYPE_MAP[activo.tipo],
                "description": activo.descripcion,
                "value_d": 5,
                "value_i": 5,
                "value_c": 5,
                "value_a": 5,
                "value_t": 5,
            }
            for i, activo in enumerate(s4.activos)
        ]
        await magerit.build_asset_inventory(analysis.id, assets_payload)

    # ─── 7) COCKPIT USER portal cliente (auth_service.create_user reuse) ──
    cockpit_user_id: uuid.UUID | None = None
    magic_link_sent = False
    try:
        from backend.app.motors.m21_portal_cliente import auth_service

        created_user, _temp_pwd = await auth_service.create_user(
            db,
            client_id=client.id,
            email=str(s5.email),
            full_name=s5.full_name,
        )
        cockpit_user_id = created_user.id
        # #7.5 · persistir cargo del usuario portal (antes se tiraba).
        cargo = getattr(s5, "cargo", None)
        if cargo:
            created_user.cargo = cargo
            await db.flush()
        magic_link_sent = False
    except Exception as exc:
        logger.warning(
            "Cockpit user creation failed durante provision · %s · admin puede "
            "crear manualmente vía /admin/clients/%s",
            exc, client.id,
        )

    # ─── 7.5) Enlazar lead al proyecto creado/promovido. Re-enlaza también si el
    #          puntero previo era inválido (proyecto borrado · CIF placeholder no
    #          reusado) → garantiza la invariante "un proyecto por lead" (#7.4).
    if lead is not None and lead.convertido_a_proyecto_id != project.id:
        lead.convertido_a_proyecto_id = project.id
        await db.flush()

    # ─── 7.6) audit_log R6 conversión (solo si el alta vino de un lead) ──
    # best-effort REAL vía SAVEPOINT · un fallo del INSERT NO aborta la
    # transacción del wizard (que commitea justo debajo).
    if lead is not None:
        try:
            async with db.begin_nested():
                await emit_conversion_audit_log(
                    db, project_id=project.id, client_id=client.id,
                    lead_id=lead.id, source="wizard",
                )
        except Exception:
            logger.exception("audit_log conversión (wizard) emit failed")

    # #10 B2 · borrador E-155 (best-effort · NO bloquea el alta).
    from backend.app.motors.m13_commercial.services.fase0_bootstrap import (
        generate_e155_draft_best_effort,
    )
    await generate_e155_draft_best_effort(db, project_id=project.id)

    # ─── 8) COMMIT atomic ──────────────────────────────────────────────
    await db.commit()
    # NO hacer db.refresh() tras el commit: con expire_on_commit=False las
    # instancias conservan sus atributos (los server defaults ya llegaron vía
    # RETURNING en el INSERT). Un refresh aquí fallaría porque los GUC RLS
    # (set_config is_local=true) se limpian al commit, así que el SELECT del
    # refresh no vería la fila recién creada ("Could not refresh instance") y
    # ADEMÁS dejaría la instancia EXPIRADA → el acceso posterior a sus columnas
    # (compute_dims_captured) dispararía un lazy-load sync → MissingGreenlet.

    from backend.app.motors.m01_categorization.dimensions_schemas import (
        compute_dims_captured,
    )
    dims_captured = compute_dims_captured(project)

    summary = (
        f"Cliente {s1.razon_social} ({s1.cif}) + proyecto {project_nombre} "
        f"creados · categoría {s3.categoria_preliminar} · "
        f"{len(departments_created)} departamentos sugeridos seedeados · "
        f"{len(s4.activos)} activos MAGERIT initial · "
        f"{'magic link enviado' if magic_link_sent else 'sin user portal'}."
    )

    return ProvisionResult(
        client_id=client.id,
        project_id=project.id,
        magerit_analysis_id=magerit_analysis_id,
        initial_system_id=initial_system.id,
        initial_information_type_id=info_type.id,
        cockpit_user_id=cockpit_user_id,
        departments_created_count=len(departments_created),
        magic_link_sent=magic_link_sent,
        dims_captured_count=dims_captured,
        summary=summary,
    )
