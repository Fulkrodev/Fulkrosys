"""Batch A diagnóstico previo · texto Art. 13 RGPD del lead (versionado).

El lead ve este texto ANTES de responder el cuestionario de diagnóstico previo.
Base jurídica: interés legítimo art. 6.1.f. El registro de consentimiento
(``precliente_diagnostic_consents.consent_text_version``) guarda la versión que
vio cada lead → si el texto cambia (v2, v3...), la prueba legal sabe qué versión
se mostró. NO modificar el texto de una versión publicada: subir la versión.

Texto v1 aportado por Marcos (verbatim · revisado).

v2 (2026-06-09): correo de contacto alineado al canónico público de Fulkro
(``marcosmata@fulkro.es`` · ``backend.app.fulkro_identity.FULKRO_EMAIL``) en lugar
del buzón admin/login ``marcos@fulkro.es``. Cambio de versión obligatorio porque el
texto está versionado para la prueba de consentimiento (NO se edita una versión ya
publicada · se sube la versión).
"""
from __future__ import annotations

ART13_PRECLIENTE_VERSION = "v2"

ART13_PRECLIENTE_TEXT = """\
Información sobre protección de datos
Responsable: Marcos Mata García (Fulkro), NIF 77171140E. Contacto: marcosmata@fulkro.es
¿Para qué tratamos tus datos? Para evaluar de forma preliminar si el Esquema Nacional de Seguridad (RD 311/2022) aplica a tu organización y preparar una posible reunión de diagnóstico.
Base jurídica: interés legítimo (art. 6.1.f RGPD) en ofrecer servicios de consultoría de seguridad a empresas que, por su actividad con el sector público, podrían estar sujetas al ENS. Hemos realizado una ponderación que concluye que este tratamiento no afecta de forma desproporcionada a tus derechos. Puedes solicitarnos información sobre dicha ponderación.
Conservación: un máximo de 12 meses desde la última interacción. Si no se inicia una relación contractual, se suprimen.
Cesiones / encargados: no cedemos datos a terceros. Nos apoyamos en proveedores que actúan como encargados del tratamiento (alojamiento e infraestructura, correo electrónico), con contratos de encargo suscritos.
Tus derechos: acceso, rectificación, supresión, limitación, portabilidad y oposición (puedes oponerte en cualquier momento al tratamiento basado en interés legítimo), escribiendo a marcosmata@fulkro.es. También puedes reclamar ante la AEPD (www.aepd.es).
"""
