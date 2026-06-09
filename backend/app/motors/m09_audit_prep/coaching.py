"""Coaching questions pre-auditoria (M9-B, spec §3.7.4).

Preguntas reales de auditores ENAC agrupadas por rol del personal
que se entrevistara.
"""
from __future__ import annotations



COACHING_QUESTIONS: dict[str, list[dict]] = {
    "direccion": [
        {
            "pregunta": (
                "¿Puede mostrarme el documento de Política de Seguridad "
                "aprobado por el órgano competente?"
            ),
            "medida": "org.1",
            "tip": (
                "Tener el PDF firmado a mano. El auditor quiere ver la firma "
                "del máximo responsable."
            ),
        },
        {
            "pregunta": (
                "¿Cómo se aprobó la categorización del sistema? "
                "¿Quién participó?"
            ),
            "medida": "org.1",
            "tip": (
                "Referenciar el Acta E-012 con los participantes y fecha."
            ),
        },
        {
            "pregunta": (
                "¿Cuál es el presupuesto asignado a seguridad de la "
                "información este año?"
            ),
            "medida": "org.1",
            "tip": (
                "Tener cifra concreta. Si no hay partida separada, explicar "
                "cómo se financia."
            ),
        },
        {
            "pregunta": (
                "¿Con qué frecuencia se reúne el Comité de Seguridad?"
            ),
            "medida": "org.1",
            "tip": (
                "Trimestral mínimo para Media. Tener actas de las últimas "
                "reuniones."
            ),
        },
        {
            "pregunta": (
                "¿Conoce los roles de Responsable de Seguridad y Responsable "
                "del Sistema? ¿Quiénes son?"
            ),
            "medida": "org.1",
            "tip": (
                "Nombrar personas concretas con nombramiento formal."
            ),
        },
    ],
    "responsable_seguridad": [
        {
            "pregunta": (
                "¿Puede mostrarme el análisis de riesgos completo con la "
                "metodología MAGERIT?"
            ),
            "medida": "op.pl.1",
            "tip": (
                "Tener E-050 con inventario, amenazas y valoración. Si es "
                "Alta, tener export PILAR."
            ),
        },
        {
            "pregunta": (
                "¿Cómo gestiona los incidentes de seguridad? Muéstreme un "
                "ejemplo reciente."
            ),
            "medida": "op.exp.7",
            "tip": (
                "Registro de incidentes con fecha, descripción, clasificación, "
                "acciones. Incluso si fueron menores."
            ),
        },
        {
            "pregunta": (
                "¿Cuál es la política de gestión de cambios? ¿Puede mostrarme "
                "un cambio reciente documentado?"
            ),
            "medida": "op.exp.5",
            "tip": (
                "Ticket/registro con solicitud, aprobación, ejecución, "
                "verificación."
            ),
        },
        {
            "pregunta": (
                "Muéstreme evidencia de que todos los usuarios tienen MFA "
                "activo."
            ),
            "medida": "op.acc.5",
            "tip": (
                "Export del directorio (AD/Entra) mostrando MFA enabled. Si "
                "no es 100%, explicar plan."
            ),
        },
        {
            "pregunta": (
                "¿Cómo se controla el acceso de proveedores externos a los "
                "sistemas?"
            ),
            "medida": "op.ext.1",
            "tip": (
                "Procedimiento + registros de accesos de terceros con "
                "fecha/hora/scope."
            ),
        },
        {
            "pregunta": (
                "¿Qué herramientas de monitorización tiene? ¿Quién revisa "
                "las alertas?"
            ),
            "medida": "op.mon.1",
            "tip": (
                "SIEM, EDR, logs. Mostrar dashboards y evidencia de que "
                "alguien los mira."
            ),
        },
    ],
    "administrador_sistemas": [
        {
            "pregunta": (
                "¿Puede mostrarme la configuración de backup y la última "
                "prueba de restauración?"
            ),
            "medida": "op.cont.1",
            "tip": (
                "Fecha última restauración exitosa, tiempo, alcance. Si no "
                "hay prueba reciente, es un finding."
            ),
        },
        {
            "pregunta": (
                "¿Cuál es el proceso de parcheo? ¿Cuántos parches críticos "
                "pendientes hay ahora mismo?"
            ),
            "medida": "op.exp.4",
            "tip": (
                "Mostrar WSUS/SCCM/Intune con estado actual. 0 críticos "
                "pendientes es el objetivo."
            ),
        },
        {
            "pregunta": (
                "¿Cómo se gestionan las cuentas de servicio? ¿Tienen dueño "
                "documentado?"
            ),
            "medida": "op.acc.1",
            "tip": (
                "Lista de service accounts con propietario, última revisión, "
                "política de contraseña."
            ),
        },
        {
            "pregunta": (
                "Muéstreme los logs de acceso a la base de datos de "
                "producción de la última semana."
            ),
            "medida": "op.exp.8",
            "tip": (
                "Logs reales. Si no hay logging de DB, es un gap crítico."
            ),
        },
    ],
    "dpo_legal": [
        {
            "pregunta": (
                "¿Existe un registro de actividades de tratamiento (RAT) "
                "actualizado?"
            ),
            "medida": "mp.info.1",
            "tip": (
                "Obligatorio por RGPD. Tenerlo en formato AEPD."
            ),
        },
        {
            "pregunta": (
                "¿Cómo se gestionan las brechas de datos personales?"
            ),
            "medida": "op.exp.7",
            "tip": (
                "Procedimiento de notificación 72h a AEPD. Tener template "
                "y registro."
            ),
        },
        {
            "pregunta": (
                "¿Los contratos con encargados de tratamiento incluyen las "
                "cláusulas del art. 28 RGPD?"
            ),
            "medida": "op.ext.1",
            "tip": (
                "Mostrar cláusulas tipo. Si hay proveedores sin contrato "
                "actualizado, es finding."
            ),
        },
    ],
}


# Heuristica simple: medidas obligatorias por categoria.
# Para CATEGORIA BASICA omitimos preguntas de DPO (muchos clientes
# BASICA son PYME sin DPO formal).
_CATEGORIA_ROLES = {
    "BASICA": {"direccion", "responsable_seguridad", "administrador_sistemas"},
    "MEDIA": {"direccion", "responsable_seguridad",
              "administrador_sistemas", "dpo_legal"},
    "ALTA": {"direccion", "responsable_seguridad",
             "administrador_sistemas", "dpo_legal"},
}


def get_questions_by_role(role: str) -> list[dict]:
    return list(COACHING_QUESTIONS.get(role, []))


def get_all_roles() -> list[str]:
    return list(COACHING_QUESTIONS.keys())


def get_questions_by_measure(measure_code: str) -> list[dict]:
    code = (measure_code or "").strip()
    out: list[dict] = []
    for role, questions in COACHING_QUESTIONS.items():
        for q in questions:
            if q.get("medida") == code:
                out.append({**q, "role": role})
    return out


def generate_coaching_pack(categoria: str) -> dict:
    cat = (categoria or "").strip().upper()
    allowed = _CATEGORIA_ROLES.get(cat, set(COACHING_QUESTIONS.keys()))
    pack: dict[str, list[dict]] = {}
    total = 0
    for role, questions in COACHING_QUESTIONS.items():
        if role not in allowed:
            continue
        pack[role] = list(questions)
        total += len(questions)
    return {
        "categoria": cat,
        "roles_cubiertos": sorted(pack.keys()),
        "questions_by_role": pack,
        "total_questions": total,
    }
