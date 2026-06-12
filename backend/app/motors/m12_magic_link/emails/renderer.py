"""Render rich HTML emails for magic links.

Single entry point :func:`render_email_for_magic_link`. Given a
``MagicLinkPurpose`` and a context dict with ``cliente``, ``proyecto``,
``destinatario``, ``link_url``, ``otp`` (optional) and ``expires_at``,
returns ``(subject, html_body, text_body)``.

The design is data-driven: each purpose has a ``PurposeEmailConfig``
with short copy for the three WHAT / WHY / WHEN slots of the base
layout. Consultant signs off as "Marcos Mata García, Consultor
independiente en Esquema Nacional de Seguridad". Nothing internal
(Motor X / Agente X) leaks.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import jinja2

from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose


FULKRO_NAVY = "#0B1F3A"
FULKRO_SPARK = "#E85D04"
FULKRO_PAPER = "#FFF8F0"
FULKRO_SILVER = "#6B7280"


BASE_HTML = """\
<!DOCTYPE html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ subject | e }}</title>
  </head>
  <body style="margin:0; padding:0; background:#F0EDEA; font-family:'Inter', 'Helvetica Neue', Arial, sans-serif; color:#0B1F3A;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F0EDEA; padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px; background:#FFF8F0; border-radius:10px; overflow:hidden; box-shadow:0 2px 14px rgba(11,31,58,.08);">

            <!-- Header -->
            <tr>
              <td style="padding:28px 32px 18px 32px; border-bottom:3px solid {{ spark }};">
                <table role="presentation" width="100%"><tr>
                  <td style="color:{{ navy }}; font-size:11px; letter-spacing:1.8px; text-transform:uppercase; font-weight:600;">
                    Proyecto {{ proyecto.nombre | e }} · {{ proyecto.codigo_documento_base | default('POL') | e }}-{{ proyecto.numero_documento | default('001') | e }}
                  </td>
                  <td style="text-align:right; color:{{ silver }}; font-size:11px;">
                    {{ fecha_envio | e }}
                  </td>
                </tr></table>
              </td>
            </tr>

            <!-- Salutation -->
            <tr>
              <td style="padding:28px 32px 0 32px;">
                <p style="margin:0 0 6px 0; font-size:14px; color:{{ silver }};">Para: {{ destinatario.nombre | e }}, {{ destinatario.cargo | default('') | e }}</p>
                <h1 style="margin:0; font-size:22px; line-height:1.3; color:{{ navy }}; font-weight:600;">{{ titulo | e }}</h1>
              </td>
            </tr>

            <!-- WHAT -->
            <tr>
              <td style="padding:26px 32px 0 32px;">
                <p style="margin:0 0 8px 0; font-size:13px; color:{{ spark }}; font-weight:600; text-transform:uppercase; letter-spacing:1px;">QUÉ debe hacer</p>
                <p style="margin:0; font-size:15px; line-height:1.55;">{{ que_hacer | e }}</p>
              </td>
            </tr>

            <!-- WHY -->
            <tr>
              <td style="padding:18px 32px 0 32px;">
                <p style="margin:0 0 8px 0; font-size:13px; color:{{ spark }}; font-weight:600; text-transform:uppercase; letter-spacing:1px;">POR QUÉ</p>
                <p style="margin:0; font-size:15px; line-height:1.55;">{{ por_que | e }}</p>
              </td>
            </tr>

            <!-- WHEN -->
            <tr>
              <td style="padding:18px 32px 0 32px;">
                <p style="margin:0 0 8px 0; font-size:13px; color:{{ spark }}; font-weight:600; text-transform:uppercase; letter-spacing:1px;">CUÁNDO</p>
                <p style="margin:0; font-size:15px; line-height:1.55;">{{ cuando | e }}</p>
                <p style="margin:8px 0 0 0; font-size:14px; color:{{ silver }};">Este enlace caduca el <strong>{{ expires_at_human | e }}</strong>.</p>
              </td>
            </tr>

            <!-- CTA -->
            <tr>
              <td style="padding:28px 32px 0 32px;" align="center">
                <table role="presentation" cellpadding="0" cellspacing="0"><tr>
                  <td style="background:{{ navy }}; border-radius:8px;">
                    <a href="{{ link_url | e }}" style="display:inline-block; padding:14px 28px; color:#FFF8F0; text-decoration:none; font-size:15px; font-weight:600; letter-spacing:.3px;">{{ action_label | e }} &rarr;</a>
                  </td>
                </tr></table>
                {% if otp %}
                <p style="margin:16px 0 0 0; font-size:13px; color:{{ silver }};">Al pulsar el botón se le solicitará el siguiente código de un solo uso (válido durante 15 minutos desde la llegada de este correo):</p>
                <p style="margin:10px 0 0 0; font-family:'JetBrains Mono','Menlo',monospace; font-size:22px; font-weight:700; color:{{ navy }}; letter-spacing:6px;">{{ otp | e }}</p>
                {% endif %}
              </td>
            </tr>

            <!-- Fallback URL -->
            <tr>
              <td style="padding:24px 32px 8px 32px;">
                <p style="margin:0; font-size:12px; color:{{ silver }};">Si el botón no funciona, copie este enlace en su navegador:</p>
                <p style="margin:4px 0 0 0; font-size:12px; color:{{ navy }}; word-break:break-all;"><a href="{{ link_url | e }}" style="color:{{ navy }};">{{ link_url | e }}</a></p>
              </td>
            </tr>

            <!-- Extra info / warnings -->
            {% if seguridad_nota %}
            <tr>
              <td style="padding:18px 32px 0 32px;">
                <div style="padding:14px 16px; background:#FFF1E3; border-left:3px solid {{ spark }}; font-size:13px; line-height:1.5;">
                  <strong>Aviso de seguridad:</strong> {{ seguridad_nota | e }}
                </div>
              </td>
            </tr>
            {% endif %}

            <!-- Signature -->
            <tr>
              <td style="padding:32px 32px 16px 32px; border-top:1px solid #E5E1DC;">
                <p style="margin:0; font-size:14px; line-height:1.5;">Un cordial saludo,</p>
                <p style="margin:10px 0 0 0; font-size:15px; font-weight:600; color:{{ navy }};">Marcos Mata García</p>
                <p style="margin:2px 0 0 0; font-size:13px; color:{{ silver }};">Consultor independiente en Esquema Nacional de Seguridad</p>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="padding:16px 32px 28px 32px; font-size:11px; line-height:1.5; color:{{ silver }};">
                Este correo forma parte del proyecto de adecuación al Esquema Nacional de Seguridad de {{ cliente.razon_social | e }} ({{ cliente.cif | e }}).
                Si lo ha recibido por error, por favor infórmenos respondiendo a este mensaje y bórrelo.
                Tratamos sus datos como responsables del proyecto conforme al Reglamento (UE) 2016/679 (RGPD).
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


TEXT_FALLBACK = """\
{subject}

Para: {destinatario_nombre}, {destinatario_cargo}

{titulo}

QUÉ HACER
{que_hacer}

POR QUÉ
{por_que}

CUÁNDO
{cuando}

Este enlace caduca el {expires_at_human}.

Abra el enlace seguro:
{link_url}
{otp_line}
{seguridad_line}

Un cordial saludo,
Marcos Mata García
Consultor independiente en Esquema Nacional de Seguridad

— Proyecto {proyecto_nombre} · {cliente_razon_social} ({cliente_cif})
"""


@dataclass(frozen=True)
class PurposeEmailConfig:
    subject: str
    titulo: str
    que_hacer: str
    por_que: str
    cuando: str
    action_label: str
    seguridad_nota: str = ""


# Sprint Polish block 3 · Opción α cleanup (2026-05-12).
# 4 PurposeEmailConfig dormantes eliminados (purposes hard-revoked por
# ADR-020 v3 SAN-E v3.MB-4.bis3 · commit 89da6e1):
#     APROBACION_FACTURA · VALIDACION_CAMBIO_ALCANCE
#     ACEPTACION_RIESGO_RESIDUAL · CONSENTIMIENTO_TRATAMIENTO_DATOS
# El cliente con cuenta portal cliente firma/aprueba in-portal. El
# `MagicLinkPolicyEnforcer.validate_purpose()` hard-rejecta su generación
# antes de llegar a este renderer. Reactivación: añadir dict literal aquí.
_PURPOSE_EMAILS: dict[MagicLinkPurpose, PurposeEmailConfig] = {
    MagicLinkPurpose.FIRMA_DOCUMENTO: PurposeEmailConfig(
        subject="Firma del documento {doc_codigo} — {cliente_razon}",
        titulo="Le solicitamos su firma sobre {doc_codigo} — {doc_titulo}.",
        que_hacer=(
            "Pulsar el botón seguro de abajo, revisar el documento en pantalla "
            "y aplicar su firma digital validada con un código de un solo uso."
        ),
        por_que=(
            "El Real Decreto 311/2022 (Esquema Nacional de Seguridad) y el ciclo "
            "de gobernanza del SGSI exigen que los documentos clave queden "
            "formalmente aprobados por el responsable competente antes de su "
            "publicación y uso. Su firma cierra el ciclo de aprobación del "
            "documento indicado."
        ),
        cuando=(
            "Idealmente en las próximas 48 horas para no bloquear las fases "
            "dependientes del proyecto."
        ),
        action_label="Firmar el documento",
        seguridad_nota=(
            "Nunca le pediremos su usuario ni contraseña habitual. El código "
            "de un solo uso sólo funciona una vez y expira en 15 minutos."
        ),
    ),
    MagicLinkPurpose.APORTE_EVIDENCIA: PurposeEmailConfig(
        subject="Aporte de evidencias para {medida_codigo} — {cliente_razon}",
        titulo="Necesitamos evidencias sobre la medida {medida_codigo}.",
        que_hacer=(
            "Abra el enlace seguro y cargue en él los ficheros solicitados "
            "(capturas, informes, registros, configuraciones). Puede subir "
            "hasta 3 lotes separados en la misma sesión."
        ),
        por_que=(
            "Las evidencias documentales son el soporte con el que se demuestra "
            "al auditor ENAC que la medida {medida_codigo} del Anexo II del ENS "
            "se encuentra efectivamente implantada en sus sistemas."
        ),
        cuando=(
            "Antes del {fecha_objetivo}, fecha en la que se congela el expediente "
            "de esta medida para su inclusión en el informe de adecuación."
        ),
        action_label="Subir evidencias",
    ),
    MagicLinkPurpose.ONBOARDING_INICIAL: PurposeEmailConfig(
        subject="Onboarding inicial del proyecto ENS — {cliente_razon}",
        titulo="Arranque del proyecto: información inicial del sistema.",
        que_hacer=(
            "Completar el cuestionario estructurado de onboarding. Incluye "
            "inventario de sistemas, servicios, responsables, proveedores y "
            "contexto regulatorio aplicable."
        ),
        por_que=(
            "Los datos recogidos alimentan el análisis de riesgos MAGERIT, la "
            "categorización y el alcance del SGSI. Sin ellos no puede "
            "arrancar la Fase 1 del proyecto."
        ),
        cuando=(
            "En el plazo de una semana desde la recepción de este mensaje para "
            "no desviar el cronograma acordado."
        ),
        action_label="Completar onboarding",
    ),
    MagicLinkPurpose.APROBACION_ACTA: PurposeEmailConfig(
        subject="Aprobación del acta {acta_codigo} — {cliente_razon}",
        titulo="Le solicitamos la aprobación del acta {acta_codigo}.",
        que_hacer=(
            "Revisar el acta de la última sesión y confirmar su aprobación, "
            "o bien solicitar aclaraciones antes de darla por válida."
        ),
        por_que=(
            "El acta formaliza las decisiones y acuerdos tomados. Su aprobación "
            "cierra el bucle documental exigido por el ciclo PDCA del SGSI y "
            "por la guía CCN-STIC 805 sobre política de seguridad."
        ),
        cuando="En el plazo de 3 días desde la recepción de este mensaje.",
        action_label="Aprobar el acta",
    ),
    MagicLinkPurpose.RESPUESTA_REQUERIMIENTO_AUDITOR: PurposeEmailConfig(
        subject="Requerimiento del auditor — respuesta urgente {ref_requerimiento}",
        titulo="Requerimiento del auditor: respuesta urgente.",
        que_hacer=(
            "Abrir el enlace, revisar el requerimiento formulado por el equipo "
            "auditor y aportar la información o documentación solicitada."
        ),
        por_que=(
            "Durante el proceso de auditoría, los requerimientos deben ser "
            "respondidos en plazo para no afectar al resultado de la "
            "certificación o causar no conformidades por falta de evidencia."
        ),
        cuando="En el plazo máximo de 48 horas desde la recepción del requerimiento.",
        action_label="Responder al auditor",
        seguridad_nota=(
            "Este enlace requiere un código de un solo uso por tratarse de "
            "información potencialmente sensible para la auditoría."
        ),
    ),
    # AUTORIZACION_PENTEST email config eliminado SAN-B.MB-6.6 ·
    # superseded por AUTORIZAR_PENTEST_EXTERNO (M8 v5.1).
    MagicLinkPurpose.AUTORIZACION_ACCION_REMOTA: PurposeEmailConfig(
        subject="AUTORIZACIÓN — Acción técnica remota sobre {alcance_corto}",
        titulo="Autorización formal de una acción técnica remota.",
        que_hacer=(
            "Revisar el alcance y el impacto de la acción técnica remota "
            "propuesta (reconfiguración, cambio de parámetros, verificación) "
            "y autorizar su ejecución con el código de un solo uso."
        ),
        por_que=(
            "Toda intervención remota sobre los sistemas del cliente debe "
            "quedar trazada y autorizada expresamente para preservar la "
            "trazabilidad exigida por el ENS (dimensión T) y por la auditoría."
        ),
        cuando="Antes de la ventana técnica programada ({ventana_inicio}).",
        action_label="Autorizar la acción",
        seguridad_nota=(
            "Si no reconoce esta solicitud, NO autorice y contacte con "
            "Marcos Mata García inmediatamente."
        ),
    ),
    MagicLinkPurpose.APROBACION_OBLIGACION: PurposeEmailConfig(
        subject="Aprobación de la obligación {obligacion_codigo} — {cliente_razon}",
        titulo="Aprobación requerida sobre {obligacion_codigo}.",
        que_hacer=(
            "Revisar el enunciado de la obligación, su entregable asociado y "
            "el plazo estimado; confirmar la aprobación para incorporarla al "
            "plan de adecuación del proyecto."
        ),
        por_que=(
            "La obligación forma parte del Plan de Adecuación y su aprobación "
            "por el responsable correspondiente es un requisito del ciclo de "
            "gobernanza del SGSI."
        ),
        cuando="En el plazo de 3 días desde la recepción de este mensaje.",
        action_label="Aprobar la obligación",
    ),
    MagicLinkPurpose.DESCARGA_DOSSIER_FINAL: PurposeEmailConfig(
        subject="Dossier final de auditoría — {cliente_razon}",
        titulo="Ya está disponible el dossier final de auditoría.",
        que_hacer=(
            "Descargar el dossier consolidado del proyecto (ZIP firmado "
            "digitalmente) para su entrega al auditor ENAC o para su archivo "
            "interno."
        ),
        por_que=(
            "El dossier contiene todos los entregables, evidencias y registros "
            "del proyecto consolidados conforme a la guía CCN-STIC 802 sobre "
            "auditoría del ENS. Es la pieza clave que el auditor revisará "
            "durante la auditoría externa."
        ),
        cuando=(
            "El enlace permite hasta 3 descargas en los próximos 7 días. "
            "Descargue el fichero y guárdelo en su repositorio documental."
        ),
        action_label="Descargar el dossier",
        seguridad_nota=(
            "El ZIP va firmado con Ed25519. Verifique la firma con el "
            "certificado público del proyecto antes de distribuir el dossier."
        ),
    ),

    # ════════════════════════════════════════════════════════════════
    # M8 v5.1 — Verificación Técnica (Sesión 7)
    # ════════════════════════════════════════════════════════════════

    MagicLinkPurpose.AUTORIZAR_VERIFICACION_TECNICA: PurposeEmailConfig(
        subject="Autorización para verificación técnica — {cliente_razon}",
        titulo=(
            "Le solicitamos la autorización formal para la verificación "
            "técnica del entorno."
        ),
        que_hacer=(
            "Revisar el alcance de la verificación (sistemas y servicios "
            "incluidos, ventana de ejecución prevista) y autorizar "
            "expresamente la ejecución con un código de un solo uso."
        ),
        por_que=(
            "La verificación técnica explora vulnerabilidades activas sobre "
            "los sistemas en producción. Sin la autorización del responsable "
            "de seguridad, ningún escaneo puede ejecutarse. La autorización "
            "queda registrada en el expediente del proyecto y a disposición "
            "del auditor ENAC."
        ),
        cuando=(
            "En el plazo máximo de 48 horas desde la recepción de este "
            "mensaje. La verificación está programada para ejecutarse en "
            "ventana nocturna ({ventana_inicio}) sin impacto en producción."
        ),
        action_label="Autorizar la verificación",
        seguridad_nota=(
            "Si no reconoce esta solicitud, NO autorice y contacte con "
            "Marcos Mata García inmediatamente."
        ),
    ),

    MagicLinkPurpose.AUTORIZAR_PENTEST_EXTERNO: PurposeEmailConfig(
        subject="Autorización para pentesting externo — {cliente_razon}",
        titulo=(
            "Le solicitamos la autorización formal para el pentesting "
            "externo del sistema."
        ),
        que_hacer=(
            "Revisar el alcance técnico del engagement (rangos de red, "
            "ventana de ejecución, datos del pentester certificado OSCP) y "
            "autorizar expresamente la realización del pentest con un "
            "código de un solo uso."
        ),
        por_que=(
            "La realización de pruebas de intrusión sin autorización expresa "
            "del titular del sistema puede constituir un acto ilícito. Esta "
            "autorización formal habilita al pentester certificado a ejecutar "
            "técnicas activas de explotación dentro del alcance acordado, y "
            "queda registrada en el expediente del proyecto. Sin ella, el "
            "pentester no recibe acceso a la VPN ni a los inventarios."
        ),
        cuando=(
            "En el plazo de 72 horas desde la recepción de este mensaje. "
            "El engagement comienza el {ventana_inicio} y se extiende hasta "
            "el {fecha_objetivo}."
        ),
        action_label="Autorizar el pentest externo",
        seguridad_nota=(
            "El enlace caduca en 72 horas por motivos de seguridad. Si no "
            "reconoce esta solicitud, NO autorice y contacte con Marcos "
            "Mata García inmediatamente."
        ),
    ),

    MagicLinkPurpose.PORTAL_REMEDIACION: PurposeEmailConfig(
        subject="Portal de remediación disponible — {cliente_razon}",
        titulo=(
            "Tiene a su disposición el portal de remediación de la última "
            "verificación técnica."
        ),
        que_hacer=(
            "Acceder al portal para revisar los hallazgos identificados, "
            "consultar las guías de remediación paso a paso y marcar cada "
            "hallazgo como resuelto cuando lo haya corregido. El portal "
            "verifica automáticamente la corrección tras pulsar 'Ya lo he "
            "arreglado'."
        ),
        por_que=(
            "Cada hallazgo abierto incrementa el riesgo y deja una no "
            "conformidad potencial ante el auditor ENAC. El portal le "
            "guía a remediarlos con instrucciones específicas para su "
            "entorno y deja constancia automática de cada corrección "
            "verificada como evidencia para el expediente."
        ),
        cuando=(
            "El portal estará accesible durante los próximos 90 días. "
            "Recomendamos resolver los hallazgos críticos y altos en las "
            "primeras dos semanas (acuerdo SLA por severidad)."
        ),
        action_label="Acceder al portal de remediación",
    ),

    MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO: PurposeEmailConfig(
        subject="Engagement asignado — {cliente_razon}",
        titulo=(
            "Su engagement de pentesting está listo. Acceda al portal "
            "para iniciar."
        ),
        que_hacer=(
            "Acceder al portal con el código de un solo uso para "
            "descargar la documentación de engagement (alcance, "
            "inventario de activos, mapa de red, vulnerabilidades ya "
            "detectadas, autorización firmada y NDA), recoger las "
            "credenciales de la VPN y, al finalizar, entregar el informe "
            "(PDF o formulario estructurado integrado)."
        ),
        por_que=(
            "El portal centraliza toda la información del engagement: "
            "scope, accesos, comunicación de incidencias, y el formulario "
            "estructurado para entregar findings con mapeo ENS automático. "
            "Esto reduce fricción y elimina envíos por correo de material "
            "sensible."
        ),
        cuando=(
            "El portal está disponible durante los próximos 60 días. La "
            "fecha límite para entregar el informe es el {fecha_objetivo}."
        ),
        action_label="Acceder al portal del engagement",
        seguridad_nota=(
            "Las credenciales VPN están cifradas con su clave pública. "
            "Si compromete activamente algún sistema, llame al teléfono "
            "de emergencia que figura en el portal antes de proseguir."
        ),
    ),

    MagicLinkPurpose.REVISAR_INFORME_VERIFICACION: PurposeEmailConfig(
        subject="Informe de verificación técnica disponible — {cliente_razon}",
        titulo=(
            "El informe de verificación técnica está listo para su revisión."
        ),
        que_hacer=(
            "Acceder al informe consolidado de la verificación técnica "
            "ejecutada sobre su entorno. Incluye E-702 (informe completo) "
            "y E-703 (resumen ejecutivo) con los hallazgos confirmados, "
            "el plan de remediación priorizado por severidad y la "
            "evolución respecto al scan anterior si lo hubo."
        ),
        por_que=(
            "El informe se incorpora al expediente del proyecto como "
            "evidencia de la medida op.exp.5 (gestión de vulnerabilidades) "
            "del Anexo II del RD 311/2022. Su revisión y aprobación cierra "
            "el ciclo de verificación técnica del periodo y desbloquea la "
            "siguiente fase del proyecto."
        ),
        cuando=(
            "El enlace permanece activo durante 15 días. Recomendamos "
            "revisarlo dentro de la primera semana para no demorar el "
            "calendario."
        ),
        action_label="Revisar el informe",
    ),

    # ── #37 Portal del auditor ENAC (acceso read-only al expediente) ──
    # feat/fulkro-100 · sin esta entrada render_email_for_magic_link lanzaba
    # ValueError → /generate-and-send devolvía email_sent=False (Marcos no podía
    # enviar el enlace al auditor · tenía que copiarlo a mano).
    MagicLinkPurpose.AUDITOR_PORTAL_ENAC: PurposeEmailConfig(
        subject="Acceso al portal de auditoría ENAC — {cliente_razon}",
        titulo=(
            "Le damos acceso al portal de auditoría del Esquema Nacional "
            "de Seguridad."
        ),
        que_hacer=(
            "Revisar, en modo solo lectura, el expediente de conformidad ENS "
            "del proyecto: Declaración de Aplicabilidad, análisis de riesgos "
            "MAGERIT, plan de adecuación, evidencias por medida, registro de "
            "actividad y dossier final. Puede dejar anotaciones y solicitar "
            "aclaraciones desde el propio portal."
        ),
        por_que=(
            "Este acceso da soporte a la auditoría de certificación conforme "
            "a CCN-CERT IC-01/19 y CCN-STIC 122, permitiéndole consultar la "
            "evidencia objetiva del cumplimiento del RD 311/2022 sin "
            "necesidad de cuentas permanentes."
        ),
        cuando=(
            "El enlace permanece activo durante 14 días. Le recomendamos "
            "iniciar la revisión cuanto antes para no demorar el calendario "
            "de la auditoría."
        ),
        action_label="Acceder al portal del auditor",
        seguridad_nota=(
            "Acceso de solo lectura, acotado a este proyecto y trazado en el "
            "registro de actividad inmutable."
        ),
    ),

    # ── M25 Paso 4 — cierre honesto del proyecto ─────────────────────
    MagicLinkPurpose.OFERTA_RETAINER: PurposeEmailConfig(
        subject="Continuidad tras certificación — {proyecto_nombre}",
        titulo=(
            "El proyecto está certificado. ¿Cómo desea continuar?"
        ),
        que_hacer=(
            "Decidir si desea contratar un retainer de mantenimiento "
            "(modelos R_MICRO, R_LITE, R_STD, R_PLUS o R_CRITICAL según "
            "la dedicación que necesite), tomarse tiempo para pensarlo "
            "o cerrar el proyecto ahora."
        ),
        por_que=(
            "El ENS exige mantenimiento continuado: revisiones "
            "anuales, renovación de evidencias, vigilancia de "
            "vulnerabilidades, continuidad operativa y auditoría "
            "interna. El retainer garantiza que esas obligaciones "
            "no caduquen y la certificación se mantenga viva."
        ),
        cuando=(
            "El enlace permanece activo durante 30 días. Pasado ese "
            "plazo sin respuesta se entenderá que elige no continuar "
            "y se iniciará el cierre con ventana de reactivación "
            "de 8 meses."
        ),
        action_label="Decidir continuidad",
    ),
    MagicLinkPurpose.DESCARGA_BACKUP_ARCHIVO: PurposeEmailConfig(
        subject="Backup de cierre disponible — {proyecto_nombre}",
        titulo=(
            "El archivo ZIP firmado con toda la documentación del "
            "proyecto está listo para descargar."
        ),
        que_hacer=(
            "Descargar un archivo ZIP con el dossier ENAC completo, "
            "las evidencias, facturas, documentos firmados y el audit "
            "log del proyecto. El ZIP está firmado con Ed25519 y "
            "puede verificarse externamente con la clave pública "
            "incluida en el manifest."
        ),
        por_que=(
            "En cumplimiento del derecho a la portabilidad de datos "
            "(art. 20 GDPR) se le entrega una copia completa del "
            "trabajo realizado. Puede usarla para continuar con otro "
            "consultor, para archivo interno o como respaldo ante "
            "requerimientos posteriores."
        ),
        cuando=(
            "El enlace permanece activo durante 60 días desde la "
            "generación del backup. Tras ese plazo el fichero será "
            "eliminado del almacenamiento de forma permanente."
        ),
        action_label="Descargar backup",
    ),
    MagicLinkPurpose.RECONSIDERACION_RETAINER: PurposeEmailConfig(
        subject="Última oportunidad para mantener su proyecto ENS — {proyecto_nombre}",
        titulo=(
            "Antes del cierre definitivo: ¿desea reconsiderar el "
            "retainer?"
        ),
        que_hacer=(
            "Confirmar si quiere reactivar un retainer en cualquiera "
            "de sus modalidades antes de que el proyecto entre en la "
            "fase final de archivo y borrado. Si confirma, se retoma "
            "donde estaba; si no, se generará el backup ZIP y el "
            "cierre será irreversible."
        ),
        por_que=(
            "Su proyecto entró en ventana de cierre hace 6 meses. "
            "Quedan 2 meses antes del borrado automático de los datos "
            "personales conforme al GDPR. Después de esa fecha solo "
            "podrá reactivar si tiene el backup ZIP, y únicamente "
            "durante los 60 días posteriores a su generación."
        ),
        cuando=(
            "El enlace permanece activo durante 60 días. Después el "
            "cierre seguirá su curso automático."
        ),
        action_label="Reconsiderar retainer",
    ),

    # ── M21 Portal Cliente + Agente 15 Paso 7 (Sesion 8) ──
    MagicLinkPurpose.PRIMER_ACCESO_CLIENTE: PurposeEmailConfig(
        subject="Bienvenido a FULKRO — active su acceso",
        titulo=(
            "Active su cuenta en el portal FULKRO"
        ),
        que_hacer=(
            "Establecer su contraseña definitiva y, opcionalmente, "
            "habilitar autenticación de doble factor (TOTP) para su "
            "cuenta del portal FULKRO. Tras completar este primer "
            "acceso podrá consultar documentos, evidencias, facturas "
            "y reportes del proyecto según los scopes asignados a "
            "su rol."
        ),
        por_que=(
            "Su organización ha habilitado su cuenta en la plataforma "
            "FULKRO. Por seguridad, el primer acceso requiere establecer "
            "una contraseña personal que solo usted conocerá, en lugar "
            "de distribuir contraseñas temporales por canales no "
            "seguros."
        ),
        cuando=(
            "El enlace permanece activo durante 24 horas. Si expira "
            "sin consumir, contacte con Marcos para que le envíe "
            "un nuevo enlace."
        ),
        action_label="Activar cuenta",
    ),
    MagicLinkPurpose.NORMATIVA_ALERT_CRITICAL: PurposeEmailConfig(
        subject="Alerta normativa crítica — {cliente_razon}",
        titulo=(
            "Alerta normativa detectada por vigilancia FULKRO"
        ),
        que_hacer=(
            "Revisar la alerta normativa detectada por el Agente 15 "
            "de Vigilancia Continua FULKRO y, si procede, aplicar "
            "las acciones correctivas sugeridas sobre su sistema ENS."
        ),
        por_que=(
            "La vigilancia diaria de FULKRO monitoriza CCN-CERT, BOE, "
            "AEPD, ENISA y CCN-STIC. Esta alerta se clasifica como "
            "crítica y puede requerir actualizar políticas, procedimientos "
            "o configuraciones de sus sistemas en alcance ENS."
        ),
        cuando=(
            "El enlace permanece activo durante 7 días. Recomendamos "
            "revisarlo en las primeras 72 horas."
        ),
        action_label="Revisar alerta",
    ),
    MagicLinkPurpose.RETAINER_WELCOME: PurposeEmailConfig(
        subject="Bienvenido al retainer FULKRO — {cliente_razon}",
        titulo=(
            "Comienza su mantenimiento continuado ENS"
        ),
        que_hacer=(
            "Revisar el calendario anual de actividades de mantenimiento "
            "del SGSI, los SLA comprometidos según su tier y los canales "
            "de soporte disponibles. Confirmar que el interlocutor único "
            "designado por su organización está correctamente registrado."
        ),
        por_que=(
            "Tras la certificación ENS, el retainer mantiene el SGSI "
            "vivo hasta la próxima auditoría de renovación bianual y "
            "asegura el cumplimiento continuado de las obligaciones "
            "recurrentes del RD 311/2022 (revisión anual análisis de "
            "riesgos, auditoría interna anual, vigilancia continua, "
            "comité de seguridad)."
        ),
        cuando=(
            "El enlace permanece activo durante 7 días."
        ),
        action_label="Acceder al retainer",
    ),

    # ── M23 Reporting + M27 Renewal Paso 7 final (Sesion 8) ──
    MagicLinkPurpose.REPORTE_TRIMESTRAL: PurposeEmailConfig(
        subject="Informe trimestral del retainer — {cliente_razon}",
        titulo="Su informe trimestral ENS está disponible",
        que_hacer=(
            "Descargar el informe E-801 del trimestre cerrado con RAG "
            "global, KPIs, actividades ejecutadas, vulnerabilidades, "
            "cambios normativos relevantes e incidentes gestionados."
        ),
        por_que=(
            "El informe trimestral documenta la evidencia de cumplimiento "
            "continuado del Esquema Nacional de Seguridad exigida por el "
            "RD 311/2022."
        ),
        cuando="El enlace permanece activo durante 60 días.",
        action_label="Descargar informe trimestral",
    ),
    MagicLinkPurpose.REPORTE_ANUAL: PurposeEmailConfig(
        subject="Informe anual del retainer — {cliente_razon}",
        titulo="Su informe anual ENS está disponible",
        que_hacer=(
            "Descargar el informe E-802 del año con resumen completo de "
            "cumplimiento, trends anuales, cambios normativos procesados "
            "y recomendaciones para el año siguiente."
        ),
        por_que=(
            "El informe anual es insumo obligado para la revisión por "
            "dirección (art. 12.7 RD 311/2022)."
        ),
        cuando="El enlace permanece activo durante 90 días.",
        action_label="Descargar informe anual",
    ),
    MagicLinkPurpose.RENEWAL_CAMPAIGN_DETAILS: PurposeEmailConfig(
        subject="Campaña renovación bianual — {cliente_razon}",
        titulo="Faltan 3 meses para la renovación bianual de su certificación ENS",
        que_hacer=(
            "Revisar el plan de actividades de la campaña de renovación: "
            "refresco de evidencias, simulacro auditoría interna, dossier "
            "ENAC pre-auditado y confirmación del auditor externo."
        ),
        por_que=(
            "Las certificaciones ENS tienen validez bienal (RD 311/2022) "
            "y deben renovarse con nueva auditoría ENAC. FULKRO ha "
            "generado el dossier y programado las actividades necesarias."
        ),
        cuando="El enlace permanece activo durante 120 días.",
        action_label="Ver campaña de renovación",
    ),

    # ── 12 FASE 4.5 · ADR-011 · #24-#35 (Sesion 11) ──
    MagicLinkPurpose.INVITACION_REUNION: PurposeEmailConfig(
        subject="Invitación a reunión {reunion_titulo} — {cliente_razon}",
        titulo="Le invitamos a la reunión {reunion_titulo}.",
        que_hacer=(
            "Pulsar el enlace seguro y confirmar su asistencia. La invitación "
            "incluye la fecha, hora y enlace al espacio de reunión externo "
            "(videollamada o presencial)."
        ),
        por_que=(
            "Esta sesión forma parte del cronograma de hitos del proyecto y su "
            "asistencia es relevante para garantizar la trazabilidad de las "
            "decisiones y la continuidad del expediente del SGSI."
        ),
        cuando="Antes de la fecha de la reunión ({reunion_fecha}).",
        action_label="Confirmar asistencia",
    ),
    MagicLinkPurpose.APROBACION_PROPUESTA: PurposeEmailConfig(
        subject="Aprobación de propuesta {propuesta_codigo} — {cliente_razon}",
        titulo="Le solicitamos la aprobación de la propuesta {propuesta_codigo}.",
        que_hacer=(
            "Revisar la propuesta comercial en pantalla, validar las condiciones "
            "económicas y técnicas, y confirmar su aprobación con el código de "
            "verificación que recibirá adjunto."
        ),
        por_que=(
            "La aprobación formal de la propuesta marca el inicio del compromiso "
            "comercial entre las partes y habilita la posterior firma del "
            "contrato C-001 que regula el alcance y los entregables del proyecto."
        ),
        cuando="En el plazo de 7 días desde la recepción de este mensaje.",
        action_label="Aprobar la propuesta",
        seguridad_nota=(
            "Esta aprobación tiene efectos jurídicos y queda registrada en el "
            "expediente del proyecto. El código de verificación garantiza la "
            "autenticidad de la firma."
        ),
    ),
    MagicLinkPurpose.SOLICITUD_INFORMACION: PurposeEmailConfig(
        subject="Solicitud de información — {asunto_corto}",
        titulo="Le solicitamos información sobre {asunto_corto}.",
        que_hacer=(
            "Abrir el enlace seguro, leer la solicitud detallada y aportar la "
            "respuesta o documentación correspondiente. Puede acceder varias "
            "veces durante el período de vigencia para completar su respuesta."
        ),
        por_que=(
            "La información solicitada es necesaria para avanzar en una fase "
            "específica del proyecto. Sin ella, las tareas dependientes quedan "
            "bloqueadas en el cronograma del SGSI."
        ),
        cuando="En el plazo de 14 días desde la recepción de este mensaje.",
        action_label="Responder a la solicitud",
    ),
    MagicLinkPurpose.COMUNICACION_INCIDENTE_SEGURIDAD: PurposeEmailConfig(
        subject="URGENTE — Incidente de seguridad {incidente_codigo} ({severidad})",
        titulo="Notificación de incidente de seguridad {incidente_codigo}.",
        que_hacer=(
            "Acceder al expediente del incidente, revisar la información "
            "preliminar (origen, sistemas afectados, contención inicial) y "
            "confirmar la recepción de la notificación con su firma."
        ),
        por_que=(
            "Conforme al artículo 13 del Real Decreto 311/2022 (Esquema "
            "Nacional de Seguridad) y la Instrucción Técnica de Seguridad "
            "de Notificación de Incidentes (BOE 13/04/2018), los incidentes "
            "de seguridad relevantes deben ser notificados al responsable "
            "competente del cliente y, en su caso, al CCN-CERT. La firma "
            "cierra el bucle de comunicación obligatorio."
        ),
        cuando=(
            "Inmediatamente. El enlace caduca en 24 horas por motivos de "
            "urgencia operativa."
        ),
        action_label="Confirmar la notificación",
        seguridad_nota=(
            "El código de un solo uso garantiza la autenticidad de la "
            "notificación recibida."
        ),
    ),
    MagicLinkPurpose.CONFIRMACION_CONFORMIDAD: PurposeEmailConfig(
        subject="Confirmación de conformidad pre-auditoría — {cliente_razon}",
        titulo="Confirmación del estado de conformidad antes de auditoría ENAC.",
        que_hacer=(
            "Revisar el resumen del estado de implantación del SGSI (medidas "
            "del Anexo II implantadas, evidencias recopiladas, riesgos "
            "aceptados) y confirmar formalmente que el sistema está preparado "
            "para someterse a la auditoría externa."
        ),
        por_que=(
            "La presentación a auditoría ENAC requiere una declaración formal "
            "del cliente confirmando que el sistema cumple los requisitos del "
            "Esquema Nacional de Seguridad. Esta confirmación previene "
            "presentaciones prematuras que puedan derivar en no conformidades."
        ),
        cuando="En el plazo de 7 días para no demorar la submission a ENAC.",
        action_label="Confirmar conformidad",
        seguridad_nota=(
            "Esta confirmación tiene efectos formales sobre el inicio del "
            "proceso de certificación."
        ),
    ),
    MagicLinkPurpose.DESCARGA_CERTIFICADO_CONFORMIDAD: PurposeEmailConfig(
        subject="Certificado de conformidad ENS disponible — {cliente_razon}",
        titulo="Su certificado de conformidad ENS está disponible.",
        que_hacer=(
            "Acceder al enlace seguro y descargar el certificado de "
            "conformidad emitido por la entidad de certificación tras la "
            "auditoría ENAC favorable. Puede descargarlo varias veces durante "
            "el período de vigencia del enlace."
        ),
        por_que=(
            "El certificado acredita ante terceros el cumplimiento de su "
            "organización con el Esquema Nacional de Seguridad y es "
            "habitualmente requerido en procesos de licitación pública y "
            "relaciones con la Administración."
        ),
        cuando="Disponible durante 30 días. Puede solicitar reenvío posteriormente.",
        action_label="Descargar el certificado",
    ),
    MagicLinkPurpose.VOTACION_COMITE_SEGURIDAD: PurposeEmailConfig(
        subject="Votación en Comité de Seguridad — acta {acta_codigo}",
        titulo="Le solicitamos su voto sobre el acta {acta_codigo}.",
        que_hacer=(
            "Revisar el acta de la sesión del Comité de Seguridad celebrada "
            "el {sesion_fecha} y emitir su voto (a favor, en contra o "
            "abstención) con un código de un solo uso."
        ),
        por_que=(
            "Las decisiones del Comité de Seguridad requieren el voto formal "
            "de sus miembros para quedar válidamente adoptadas conforme al "
            "reglamento interno del comité y al ciclo PDCA del SGSI."
        ),
        cuando="En el plazo de 7 días desde la convocatoria.",
        action_label="Emitir voto",
        seguridad_nota=(
            "El código de un solo uso garantiza la autenticidad e "
            "individualidad de su voto. Cada miembro dispone de un único voto "
            "por sesión."
        ),
    ),
    MagicLinkPurpose.ENCUESTA_SATISFACCION_NPS: PurposeEmailConfig(
        subject="Su valoración del servicio — {cliente_razon}",
        titulo="Nos gustaría conocer su valoración del servicio.",
        que_hacer=(
            "Acceder al enlace y responder una breve encuesta (menos de 3 "
            "minutos) sobre su experiencia con el proyecto. Su valoración "
            "incluye una pregunta principal de recomendación (NPS) y un campo "
            "abierto opcional para comentarios."
        ),
        por_que=(
            "Su feedback es clave para mejorar la calidad del servicio y "
            "ajustar la metodología en futuras colaboraciones. Los resultados "
            "se incorporan al expediente del proyecto y se utilizan de forma "
            "agregada para análisis interno de calidad."
        ),
        cuando="Disponible durante 30 días desde la recepción de este mensaje.",
        action_label="Responder la encuesta",
    ),

    # ── SAN-D MB-19.4 · ADR-041 · firma contrato comercial ──
    MagicLinkPurpose.FIRMA_CONTRATO: PurposeEmailConfig(
        subject="Firma del contrato de servicios — {cliente_razon}",
        titulo="Su contrato de servicios FULKRO está listo para la firma.",
        que_hacer=(
            "Acceder al enlace, revisar el contrato adjunto, introducir el "
            "código OTP recibido por canal separado y confirmar la firma "
            "con captura de localización geográfica. La firma queda "
            "registrada con auditoría jurídica completa (IP, user-agent, "
            "geo, timestamp)."
        ),
        por_que=(
            "La firma del contrato formaliza el inicio del proyecto de "
            "implantación ENS. Tras la firma, el cliente recibe automáticamente "
            "acceso al portal cliente FULKRO para iniciar el onboarding y "
            "consultar hitos, evidencias y el avance del proyecto en tiempo "
            "real."
        ),
        cuando=(
            "El enlace tiene validez de 72 horas desde su recepción. "
            "El código OTP es de un solo uso por intento (3 intentos máximo)."
        ),
        action_label="Firmar contrato",
    ),
}


def _format(config: PurposeEmailConfig, ctx: dict[str, Any]) -> dict[str, str]:
    """Resolve ``{placeholders}`` inside the config copy against the
    render context. Missing keys are filled with a neutral placeholder
    so rendering never fails and the email is always sendable."""
    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return f"{{{key}}}"

    safe_ctx = _SafeDict({
        "cliente_razon": ctx.get("cliente", {}).get("razon_social", ""),
        "cliente_cif": ctx.get("cliente", {}).get("cif", ""),
        "proyecto_nombre": ctx.get("proyecto", {}).get("nombre", ""),
        "doc_codigo": ctx.get("documento", {}).get("codigo", ""),
        "doc_titulo": ctx.get("documento", {}).get("titulo", ""),
        "medida_codigo": ctx.get("medida", {}).get("codigo", ""),
        "fecha_objetivo": ctx.get("fecha_objetivo", ""),
        # acta_codigo: prioridad flat key (FASE 4.5 #34) → fallback dict (legacy m18)
        "acta_codigo": ctx.get("acta_codigo")
        or ctx.get("acta", {}).get("codigo", ""),
        "ref_requerimiento": ctx.get("requerimiento", {}).get("ref", ""),
        "alcance_corto": ctx.get("alcance_corto", ""),
        "ventana_inicio": ctx.get("ventana_inicio", ""),
        "obligacion_codigo": ctx.get("obligacion", {}).get("codigo", ""),
        # FASE 4.5 sub-bloque B.1 · 10 vars ADR-011 #24-#35 (acta_codigo arriba)
        "reunion_titulo": ctx.get("reunion_titulo", ""),
        "reunion_fecha": ctx.get("reunion_fecha", ""),
        "propuesta_codigo": ctx.get("propuesta_codigo", ""),
        "factura_codigo": ctx.get("factura_codigo", ""),
        "factura_importe": ctx.get("factura_importe", ""),
        "asunto_corto": ctx.get("asunto_corto", ""),
        "cambio_codigo": ctx.get("cambio_codigo", ""),
        "riesgo_codigo": ctx.get("riesgo_codigo", ""),
        "incidente_codigo": ctx.get("incidente_codigo", ""),
        "severidad": ctx.get("severidad", ""),
        "sesion_fecha": ctx.get("sesion_fecha", ""),
    })
    return {
        "subject": config.subject.format_map(safe_ctx),
        "titulo": config.titulo.format_map(safe_ctx),
        "que_hacer": config.que_hacer.format_map(safe_ctx),
        "por_que": config.por_que.format_map(safe_ctx),
        "cuando": config.cuando.format_map(safe_ctx),
        "action_label": config.action_label,
        "seguridad_nota": config.seguridad_nota.format_map(safe_ctx) if config.seguridad_nota else "",
    }


def render_email_for_magic_link(
    purpose: MagicLinkPurpose,
    link_url: str,
    expires_at: datetime,
    cliente: dict[str, Any],
    proyecto: dict[str, Any],
    destinatario: dict[str, Any],
    otp: str | None = None,
    **extra: Any,
) -> tuple[str, str, str]:
    """Render ``(subject, html, text)`` for a magic-link email.

    ``extra`` may contain optional purpose-specific data (documento,
    medida, acta, requerimiento, alcance_corto, ventana_inicio,
    obligacion, fecha_objetivo). Unknown keys are ignored.
    """
    cfg = _PURPOSE_EMAILS.get(purpose)
    if cfg is None:
        raise ValueError(f"No email template for purpose: {purpose}")

    render_ctx: dict[str, Any] = {
        "cliente": cliente,
        "proyecto": proyecto,
        "destinatario": destinatario,
        **extra,
    }
    resolved = _format(cfg, render_ctx)

    subject = resolved["subject"]
    expires_human = expires_at.strftime("%d/%m/%Y %H:%M UTC")
    fecha_envio = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    env = jinja2.Environment(autoescape=True, undefined=jinja2.StrictUndefined)
    html = env.from_string(BASE_HTML).render(
        subject=subject,
        titulo=resolved["titulo"],
        que_hacer=resolved["que_hacer"],
        por_que=resolved["por_que"],
        cuando=resolved["cuando"],
        action_label=resolved["action_label"],
        seguridad_nota=resolved["seguridad_nota"],
        link_url=link_url,
        otp=otp,
        expires_at_human=expires_human,
        fecha_envio=fecha_envio,
        cliente=cliente,
        proyecto=proyecto,
        destinatario=destinatario,
        navy=FULKRO_NAVY,
        spark=FULKRO_SPARK,
        paper=FULKRO_PAPER,
        silver=FULKRO_SILVER,
    )

    otp_line = f"\nCódigo de un solo uso: {otp}\n" if otp else ""
    seguridad_line = (
        f"\nAviso de seguridad: {resolved['seguridad_nota']}\n"
        if resolved["seguridad_nota"] else ""
    )
    text = TEXT_FALLBACK.format(
        subject=subject,
        destinatario_nombre=destinatario.get("nombre", ""),
        destinatario_cargo=destinatario.get("cargo", ""),
        titulo=resolved["titulo"],
        que_hacer=resolved["que_hacer"],
        por_que=resolved["por_que"],
        cuando=resolved["cuando"],
        expires_at_human=expires_human,
        link_url=link_url,
        otp_line=otp_line,
        seguridad_line=seguridad_line,
        proyecto_nombre=proyecto.get("nombre", ""),
        cliente_razon_social=cliente.get("razon_social", ""),
        cliente_cif=cliente.get("cif", ""),
    )

    return subject, html, text
