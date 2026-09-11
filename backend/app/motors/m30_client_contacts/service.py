"""Motor 30 — Client Contacts: business logic.

13 métodos plan v4.2 FASE 5.5.B:
  CRUD: ``create_contact`` / ``list_contacts`` / ``get_contact_by_id`` /
        ``update_contact`` / ``deactivate_contact`` / ``activate_contact`` /
        ``delete_contact_cascade``.
  Timeline + auto-log: ``log_interaction`` / ``get_timeline``.
  Integraciones: ``get_for_copilot_context`` (A14) / ``import_csv`` /
                 ``export_csv`` / ``search_full_text``.

``log_interaction`` es el entry point cross-motor. A18 (reuniones), M14
(contratos), M29 (mensajería FASE 6) y M12 (magic links — diferido
TODO-M30-M12-INTEGRATION-001) lo invocan tras crear su entity.
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m30_client_contacts.models import (
    ClientContact,
    ClientContactInteraction,
)
from backend.app.motors.m30_client_contacts.schemas import (
    ClientContactCreate,
    ClientContactListItem,
    ClientContactOut,
    ClientContactUpdate,
    CopilotContextEntry,
    InteractionType,
    TimelineEntryOut,
)


# ====================================================================
# Excepciones de dominio
# ====================================================================


class RolEnsYaAsignadoError(Exception):
    """El contacto ya sostiene otro rol ENS y no se confirmo el reemplazo.

    P3 · el rol ENS es una columna escalar: asignar uno nuevo borra el
    anterior. El art. 13 del RD 311/2022 exige designaciones diferenciadas, asi
    que perder una en silencio deja al proyecto sin un responsable que alguien
    creia designado.
    """


class ContactNotFoundError(Exception):
    """Contacto no encontrado por id (o eliminado)."""


class DuplicateContactEmailError(Exception):
    """UniqueConstraint (client_id, email) violada."""


# ====================================================================
# Servicio
# ====================================================================


class ClientContactService:
    """Servicio de contactos cliente (motor 30)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ----------------------------------------------------------------
    # CRUD
    # ----------------------------------------------------------------

    async def create_contact(
        self,
        client_id: uuid.UUID,
        payload: ClientContactCreate,
        created_by_user_id: uuid.UUID | None = None,
    ) -> ClientContactOut:
        """Crea un contacto. Si ``is_primary=True`` desmarca otros primary."""
        if payload.is_primary:
            await self._unset_other_primary(client_id)

        contact = ClientContact(
            client_id=client_id,
            full_name=payload.full_name,
            preferred_name=payload.preferred_name,
            email=str(payload.email),
            phone=payload.phone,
            linkedin_url=str(payload.linkedin_url) if payload.linkedin_url else None,
            role_title=payload.role_title,
            role_category=payload.role_category,
            is_primary=payload.is_primary,
            is_signatory=payload.is_signatory,
            has_portal_access=payload.has_portal_access,
            role_ens_required=payload.role_ens_required,
            contact_role_notes=payload.contact_role_notes,
            notes_marcos=payload.notes_marcos,
            preferred_communication=payload.preferred_communication,
            timezone=payload.timezone,
            created_by_user_id=created_by_user_id,
        )
        self.db.add(contact)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise DuplicateContactEmailError(
                f"Ya existe contacto con email {payload.email} para este cliente"
            ) from exc
        await self.db.refresh(contact)
        return await self._to_out(contact)

    async def list_contacts(
        self,
        client_id: uuid.UUID,
        *,
        role_category: str | None = None,
        is_active: bool | None = True,
        is_signatory: bool | None = None,
        search: str | None = None,
    ) -> list[ClientContactListItem]:
        """Listado scopeado por cliente con filtros opcionales."""
        stmt = select(ClientContact).where(
            ClientContact.client_id == client_id,
            ClientContact.deleted_at.is_(None),
        )
        if role_category is not None:
            stmt = stmt.where(ClientContact.role_category == role_category)
        if is_active is not None:
            stmt = stmt.where(ClientContact.is_active == is_active)
        if is_signatory is not None:
            stmt = stmt.where(ClientContact.is_signatory == is_signatory)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    ClientContact.full_name.ilike(like),
                    ClientContact.email.ilike(like),
                    ClientContact.role_title.ilike(like),
                )
            )
        stmt = stmt.order_by(
            ClientContact.is_primary.desc(),
            ClientContact.full_name.asc(),
        )
        result = await self.db.execute(stmt)
        contacts = list(result.scalars())
        # Enriquecer last_interaction_at por contacto sin N+1.
        last_interactions = await self._latest_interactions_map(
            [c.id for c in contacts]
        )
        return [
            ClientContactListItem(
                id=c.id,
                full_name=c.full_name,
                preferred_name=c.preferred_name,
                email=c.email,
                phone=c.phone,
                role_title=c.role_title,
                role_category=c.role_category,
                is_primary=c.is_primary,
                is_signatory=c.is_signatory,
                has_portal_access=c.has_portal_access,
                is_active=c.is_active,
                last_interaction_at=last_interactions.get(c.id, (None, None))[0],
                last_interaction_type=last_interactions.get(c.id, (None, None))[1],
            )
            for c in contacts
        ]

    async def get_contact_by_id(
        self, contact_id: uuid.UUID,
    ) -> ClientContactOut:
        """Detalle por id. Lanza ContactNotFoundError si no existe."""
        contact = await self._get_or_404(contact_id)
        return await self._to_out(contact)

    async def update_contact(
        self,
        contact_id: uuid.UUID,
        payload: ClientContactUpdate,
    ) -> ClientContactOut:
        """Actualización parcial PATCH semantics."""
        contact = await self._get_or_404(contact_id)

        if payload.is_primary is True:
            await self._unset_other_primary(contact.client_id, exclude_id=contact_id)

        data = payload.model_dump(exclude_unset=True)
        if "linkedin_url" in data and data["linkedin_url"] is not None:
            data["linkedin_url"] = str(data["linkedin_url"])
        if "email" in data and data["email"] is not None:
            data["email"] = str(data["email"])

        for k, v in data.items():
            setattr(contact, k, v)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise DuplicateContactEmailError(
                "Email duplicado para este cliente"
            ) from exc
        await self.db.refresh(contact)
        return await self._to_out(contact)

    async def deactivate_contact(
        self, contact_id: uuid.UUID, reason: str,
    ) -> ClientContactOut:
        """Soft-state: marca is_active=False, conserva history e interacciones."""
        contact = await self._get_or_404(contact_id)
        contact.is_active = False
        contact.inactive_reason = reason
        contact.inactive_since = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(contact)
        return await self._to_out(contact)

    async def activate_contact(
        self, contact_id: uuid.UUID,
    ) -> ClientContactOut:
        """Re-activa un contacto previamente desactivado."""
        contact = await self._get_or_404(contact_id)
        contact.is_active = True
        contact.inactive_reason = None
        contact.inactive_since = None
        await self.db.flush()
        await self.db.refresh(contact)
        return await self._to_out(contact)

    async def delete_contact_cascade(self, contact_id: uuid.UUID) -> None:
        """Hard delete: elimina contact + interactions (FK CASCADE)."""
        contact = await self._get_or_404(contact_id)
        await self.db.delete(contact)
        await self.db.flush()

    # ----------------------------------------------------------------
    # Timeline + log_interaction (entry point cross-motor)
    # ----------------------------------------------------------------

    async def log_interaction(
        self,
        contact_id: uuid.UUID,
        interaction_type: InteractionType,
        *,
        source_motor: str | None = None,
        source_id: uuid.UUID | None = None,
        summary: str | None = None,
        details: dict | None = None,
    ) -> uuid.UUID:
        """Registra una interacción para un contacto.

        Entry point invocado por servicios cross-motor (A18/M29/M12/M14)
        post-creación de su entity. NO valida contacto activo — un
        contacto desactivado puede recibir interacciones residuales
        (ej. firma final tras desactivación administrativa).

        Returns the new interaction id.
        """
        # Verificar existencia (no _get_or_404 porque deactivate keeps row).
        stmt = select(ClientContact.id).where(
            ClientContact.id == contact_id,
            ClientContact.deleted_at.is_(None),
        )
        if (await self.db.execute(stmt)).scalar_one_or_none() is None:
            raise ContactNotFoundError(
                f"Contacto {contact_id} no existe o está eliminado"
            )

        interaction = ClientContactInteraction(
            contact_id=contact_id,
            interaction_type=interaction_type,
            source_motor=source_motor,
            source_id=source_id,
            summary=summary,
            details=details,
        )
        self.db.add(interaction)
        await self.db.flush()
        await self.db.refresh(interaction)
        return interaction.id

    async def get_timeline(
        self,
        contact_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[TimelineEntryOut]:
        """Devuelve interacciones más recientes primero (DESC by created_at)."""
        await self._get_or_404(contact_id)  # validar existe
        stmt = (
            select(ClientContactInteraction)
            .where(ClientContactInteraction.contact_id == contact_id)
            .order_by(desc(ClientContactInteraction.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = list(result.scalars())
        return [
            TimelineEntryOut(
                id=r.id,
                interaction_type=r.interaction_type,
                source_motor=r.source_motor,
                source_id=r.source_id,
                summary=r.summary,
                details=r.details,
                occurred_at=r.created_at,
            )
            for r in rows
        ]

    # ----------------------------------------------------------------
    # Integraciones
    # ----------------------------------------------------------------

    async def get_for_copilot_context(
        self, client_id: uuid.UUID,
    ) -> list[CopilotContextEntry]:
        """Formatea contactos activos para inyectar en system prompt A14.

        Devuelve líneas pre-renderizadas. A14 las concatena a su prompt
        con un header tipo ``## Contexto cliente (M30)``.
        """
        stmt = select(ClientContact).where(
            ClientContact.client_id == client_id,
            ClientContact.is_active.is_(True),
            ClientContact.deleted_at.is_(None),
        ).order_by(
            ClientContact.is_primary.desc(),
            ClientContact.is_signatory.desc(),
            ClientContact.full_name.asc(),
        )
        result = await self.db.execute(stmt)
        contacts = list(result.scalars())

        entries: list[CopilotContextEntry] = []
        for c in contacts:
            tags: list[str] = []
            if c.is_primary:
                tags.append("PRIMARY")
            if c.is_signatory:
                tags.append("SIGNATORY")
            tag_suffix = f" [{', '.join(tags)}]" if tags else ""
            notes_excerpt = (
                c.notes_marcos[:200] if c.notes_marcos else None
            )
            line = (
                f"- {c.full_name} ({c.role_title}, {c.role_category})"
                f"{tag_suffix}"
            )
            if notes_excerpt:
                line += f" — Notas: {notes_excerpt}"
            entries.append(
                CopilotContextEntry(
                    full_name=c.full_name,
                    role_title=c.role_title,
                    role_category=c.role_category,
                    is_primary=c.is_primary,
                    is_signatory=c.is_signatory,
                    notes_excerpt=notes_excerpt,
                    formatted_line=line,
                )
            )
        return entries

    async def import_csv(
        self,
        client_id: uuid.UUID,
        csv_content: str,
        created_by_user_id: uuid.UUID | None = None,
    ) -> list[ClientContactOut]:
        """Importa contactos desde CSV.

        Columnas requeridas: ``full_name,email,role_title,role_category``.
        Columnas opcionales: ``preferred_name,phone,linkedin_url,
        is_primary,is_signatory,has_portal_access,notes_marcos,
        preferred_communication,timezone``.

        Filas con email duplicado se omiten silenciosamente — el batch
        completa el resto. Devuelve los contactos creados (no las
        filas omitidas).
        """
        reader = csv.DictReader(io.StringIO(csv_content))
        created: list[ClientContactOut] = []
        for row in reader:
            payload_data = {
                "full_name": row["full_name"],
                "email": row["email"],
                "role_title": row["role_title"],
                "role_category": row["role_category"],
                "preferred_name": row.get("preferred_name") or None,
                "phone": row.get("phone") or None,
                "linkedin_url": row.get("linkedin_url") or None,
                "is_primary": _parse_bool(row.get("is_primary")),
                "is_signatory": _parse_bool(row.get("is_signatory")),
                "has_portal_access": _parse_bool(row.get("has_portal_access")),
                "notes_marcos": row.get("notes_marcos") or None,
                "preferred_communication": row.get("preferred_communication") or None,
                "timezone": row.get("timezone") or "Europe/Madrid",
            }
            try:
                payload = ClientContactCreate(**payload_data)
                contact = await self.create_contact(
                    client_id, payload, created_by_user_id,
                )
                created.append(contact)
            except DuplicateContactEmailError:
                continue
        return created

    async def export_csv(self, client_id: uuid.UUID) -> str:
        """Exporta contactos del cliente a CSV con columnas estándar."""
        stmt = select(ClientContact).where(
            ClientContact.client_id == client_id,
            ClientContact.deleted_at.is_(None),
        ).order_by(ClientContact.full_name.asc())
        result = await self.db.execute(stmt)
        contacts = list(result.scalars())

        out = io.StringIO()
        fieldnames = [
            "full_name", "preferred_name", "email", "phone",
            "linkedin_url", "role_title", "role_category",
            "is_primary", "is_signatory", "has_portal_access",
            "notes_marcos", "preferred_communication", "timezone",
            "is_active",
        ]
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        for c in contacts:
            writer.writerow({
                "full_name": c.full_name,
                "preferred_name": c.preferred_name or "",
                "email": c.email,
                "phone": c.phone or "",
                "linkedin_url": c.linkedin_url or "",
                "role_title": c.role_title,
                "role_category": c.role_category,
                "is_primary": "true" if c.is_primary else "false",
                "is_signatory": "true" if c.is_signatory else "false",
                "has_portal_access": "true" if c.has_portal_access else "false",
                "notes_marcos": c.notes_marcos or "",
                "preferred_communication": c.preferred_communication or "",
                "timezone": c.timezone,
                "is_active": "true" if c.is_active else "false",
            })
        return out.getvalue()

    async def search_full_text(
        self, client_id: uuid.UUID, query: str,
    ) -> list[ClientContactListItem]:
        """Búsqueda GIN sobre notes_marcos + ILIKE name/role como fallback.

        El índice GIN ``ix_client_contacts_notes_fts`` indexa
        ``to_tsvector('spanish', notes_marcos)``.
        """
        if not query.strip():
            return []
        ts_query = func.plainto_tsquery("spanish", query)
        stmt = select(ClientContact).where(
            ClientContact.client_id == client_id,
            ClientContact.deleted_at.is_(None),
            or_(
                func.to_tsvector(
                    "spanish",
                    func.coalesce(ClientContact.notes_marcos, ""),
                ).op("@@")(ts_query),
                ClientContact.full_name.ilike(f"%{query}%"),
                ClientContact.role_title.ilike(f"%{query}%"),
            ),
        ).order_by(ClientContact.full_name.asc())
        result = await self.db.execute(stmt)
        contacts = list(result.scalars())
        last = await self._latest_interactions_map([c.id for c in contacts])
        return [
            ClientContactListItem(
                id=c.id,
                full_name=c.full_name,
                preferred_name=c.preferred_name,
                email=c.email,
                phone=c.phone,
                role_title=c.role_title,
                role_category=c.role_category,
                is_primary=c.is_primary,
                is_signatory=c.is_signatory,
                has_portal_access=c.has_portal_access,
                is_active=c.is_active,
                last_interaction_at=last.get(c.id, (None, None))[0],
                last_interaction_type=last.get(c.id, (None, None))[1],
            )
            for c in contacts
        ]

    # ----------------------------------------------------------------
    # Helpers privados
    # ----------------------------------------------------------------

    async def _get_or_404(self, contact_id: uuid.UUID) -> ClientContact:
        stmt = select(ClientContact).where(
            ClientContact.id == contact_id,
            ClientContact.deleted_at.is_(None),
        )
        contact = (await self.db.execute(stmt)).scalar_one_or_none()
        if contact is None:
            raise ContactNotFoundError(
                f"Contacto {contact_id} no existe o está eliminado"
            )
        return contact

    async def _unset_other_primary(
        self,
        client_id: uuid.UUID,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        """Garantiza que sólo un contacto sea is_primary por cliente."""
        stmt = (
            update(ClientContact)
            .where(
                ClientContact.client_id == client_id,
                ClientContact.is_primary.is_(True),
                ClientContact.deleted_at.is_(None),
            )
            .values(is_primary=False)
        )
        if exclude_id is not None:
            stmt = stmt.where(ClientContact.id != exclude_id)
        await self.db.execute(stmt)

    async def _latest_interactions_map(
        self, contact_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, tuple[datetime, str]]:
        """Map contact_id → (created_at, interaction_type) más reciente.

        Una sola query DISTINCT ON (PostgreSQL) — evita N+1 en list.
        """
        if not contact_ids:
            return {}
        # DISTINCT ON con orden DESC por contact_id+created_at devuelve
        # la fila más reciente de cada contact.
        result = await self.db.execute(
            text(
                "SELECT DISTINCT ON (contact_id) contact_id, "
                "created_at, interaction_type "
                "FROM client_contact_interactions "
                "WHERE contact_id = ANY(:ids) "
                "ORDER BY contact_id, created_at DESC"
            ),
            {"ids": contact_ids},
        )
        return {
            row.contact_id: (row.created_at, row.interaction_type)
            for row in result
        }

    async def _to_out(self, contact: ClientContact) -> ClientContactOut:
        """Construye ClientContactOut con agregados timeline."""
        last_map = await self._latest_interactions_map([contact.id])
        count_stmt = select(
            func.count(ClientContactInteraction.id)
        ).where(ClientContactInteraction.contact_id == contact.id)
        count = (await self.db.execute(count_stmt)).scalar_one()
        last_at, last_type = last_map.get(contact.id, (None, None))
        return ClientContactOut(
            id=contact.id,
            client_id=contact.client_id,
            full_name=contact.full_name,
            preferred_name=contact.preferred_name,
            email=contact.email,
            phone=contact.phone,
            linkedin_url=contact.linkedin_url,
            role_title=contact.role_title,
            role_category=contact.role_category,
            is_primary=contact.is_primary,
            is_signatory=contact.is_signatory,
            has_portal_access=contact.has_portal_access,
            client_user_id=contact.client_user_id,
            notes_marcos=contact.notes_marcos,
            preferred_communication=contact.preferred_communication,
            timezone=contact.timezone,
            is_active=contact.is_active,
            inactive_reason=contact.inactive_reason,
            inactive_since=contact.inactive_since,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
            last_interaction_at=last_at,
            last_interaction_type=last_type,
            interactions_count=int(count),
        )

    # ----------------------------------------------------------------
    # ENS_REQUIRED roles · SAN-E v3.MB-5.0.bis
    # ----------------------------------------------------------------

    async def get_ens_required_roles_status(
        self,
        project_id: uuid.UUID,
    ) -> dict:
        """Status overview ENS_REQUIRED roles per project · admin widget.

        Resuelve client_id desde project_id y agrupa contactos activos con
        ``role_ens_required`` no nulo. Returns dict con cada uno de los 6
        roles + flags ``all_assigned`` · ``missing`` · counters.
        """
        from sqlalchemy import text as sa_text
        from backend.app.motors.m30_client_contacts.ens_required import (
            ENS_REQUIRED_ROLES,
        )

        row = await self.db.execute(
            sa_text("SELECT client_id FROM projects WHERE id = :pid"),
            {"pid": str(project_id)},
        )
        hit = row.first()
        if hit is None:
            raise ContactNotFoundError(
                f"project {project_id} no existe (lookup client_id)"
            )
        client_id: uuid.UUID = hit[0]

        stmt = select(ClientContact).where(
            ClientContact.client_id == client_id,
            ClientContact.role_ens_required.isnot(None),
            ClientContact.is_active.is_(True),
            ClientContact.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        contacts = result.scalars().all()

        by_role: dict[str, dict | None] = {role: None for role in ENS_REQUIRED_ROLES}
        for contact in contacts:
            role = contact.role_ens_required
            if role not in by_role:
                continue  # rol fuera del catálogo (defensa CHECK constraint)
            by_role[role] = {
                "contact_id": str(contact.id),
                "full_name": contact.full_name,
                "email": contact.email,
                "role_title": contact.role_title,
                "phone": contact.phone,
                "has_portal_access": contact.has_portal_access,
                "contact_role_notes": contact.contact_role_notes,
                "assigned_at": (
                    contact.updated_at.isoformat()
                    if contact.updated_at else contact.created_at.isoformat()
                ),
            }

        missing = [role for role, v in by_role.items() if v is None]
        return {
            "project_id": str(project_id),
            "client_id": str(client_id),
            "roles": by_role,
            "all_assigned": not missing,
            "missing": missing,
            "total_assigned": sum(1 for v in by_role.values() if v is not None),
            "total_required": len(ENS_REQUIRED_ROLES),
        }

    async def assign_ens_required_role(
        self,
        contact_id: uuid.UUID,
        role: str,
        notes: str | None = None,
        *,
        reemplazar_rol_actual: bool = False,
    ) -> tuple[ClientContact, dict[str, str]]:
        """Asigna un rol ENS_REQUIRED a un contacto · operacion de administracion.

        Devuelve ``(contacto, desplazados)``, donde ``desplazados`` dice QUE se
        perdio por el camino: ``{"rol_anterior_del_contacto": ...,
        "contactos_vaciados": "nombre (rol)"}``.

        P3 · EL DEFECTO QUE ARREGLA
            El rol vive en UNA columna escalar del contacto
            (``models.py:127``, ``role_ens_required``): no hay tabla puente, asi
            que un contacto no puede sostener dos roles. Asignarle un segundo
            PISABA el primero en la linea del final, y la operacion respondia
            200 en los dos casos. La docstring anterior lo describia como si
            fuera el disenyo -- "1 contact puede tener varios roles via
            re-asignacion sucesiva -> solo el ultimo queda activo" -- y no lo
            es: es perdida de dato sin aviso.

            Y no es un dato cualquiera. El art. 13 del RD 311/2022 exige
            designar responsable de la informacion, del servicio y de
            seguridad, diferenciados. Borrar una designacion en silencio deja
            al proyecto sin un responsable que alguien creia designado.

            Ahora, si el contacto ya tiene OTRO rol, la operacion se niega
            salvo que quien la pide diga explicitamente que quiere reemplazarlo
            (``reemplazar_rol_actual=True``). Y lo que se desplaza se devuelve
            al llamante para que lo cuente, en vez de desaparecer.
        """
        from backend.app.motors.m30_client_contacts.ens_required import (
            ENS_REQUIRED_ROLES,
        )

        if role not in ENS_REQUIRED_ROLES:
            raise ValueError(
                f"role '{role}' no esta en ENS_REQUIRED_ROLES catalogo"
            )

        contact = await self.db.get(ClientContact, contact_id)
        if contact is None or contact.deleted_at is not None:
            raise ContactNotFoundError(f"contact {contact_id} no existe")

        rol_previo = contact.role_ens_required
        if rol_previo and rol_previo != role and not reemplazar_rol_actual:
            raise RolEnsYaAsignadoError(
                f"{contact.full_name} ya tiene asignado el rol "
                f"'{rol_previo}'. Un contacto solo puede sostener un rol ENS "
                f"a la vez, asi que asignarle '{role}' le quitaria el que "
                f"tiene. Si es lo que quieres, repite la operacion "
                f"confirmando el reemplazo."
            )

        desplazados: dict[str, str] = {}
        if rol_previo and rol_previo != role:
            desplazados["rol_anterior_del_contacto"] = rol_previo

        # Vacate cualquier otro contact del mismo client con este role
        existing_stmt = select(ClientContact).where(
            ClientContact.client_id == contact.client_id,
            ClientContact.role_ens_required == role,
            ClientContact.id != contact_id,
            ClientContact.deleted_at.is_(None),
        )
        existing_result = await self.db.execute(existing_stmt)
        for other in existing_result.scalars():
            # Tambien esto era silencioso: el rol cambiaba de manos y nadie se
            # enteraba de a quien se lo quitaron.
            desplazados["contacto_vaciado"] = f"{other.full_name} ({role})"
            other.role_ens_required = None
            other.contact_role_notes = None

        contact.role_ens_required = role
        if notes is not None:
            contact.contact_role_notes = notes
        await self.db.flush()
        return contact, desplazados

    async def vacate_ens_required_role(
        self,
        contact_id: uuid.UUID,
    ) -> ClientContact:
        """Vacate ENS_REQUIRED role assignment · contact se mantiene activo."""
        contact = await self.db.get(ClientContact, contact_id)
        if contact is None or contact.deleted_at is not None:
            raise ContactNotFoundError(f"contact {contact_id} no existe")
        contact.role_ens_required = None
        contact.contact_role_notes = None
        await self.db.flush()
        return contact

    async def get_stakeholders_for_template(
        self,
        project_id: uuid.UUID,
    ) -> dict[str, dict | None]:
        """Helper para M6 Document Factory · auto-populate context per template."""
        status = await self.get_ens_required_roles_status(project_id)
        return status["roles"]


# ====================================================================
# Helpers libre-funcionales
# ====================================================================


def _parse_bool(s: str | None) -> bool:
    """Parsea valores CSV ``true|false|1|0|yes|no`` (case-insensitive)."""
    if not s:
        return False
    return s.strip().lower() in {"true", "1", "yes", "y", "si", "sí"}
