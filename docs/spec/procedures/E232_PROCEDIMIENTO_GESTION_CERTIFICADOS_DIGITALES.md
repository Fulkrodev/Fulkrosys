# DOCUMENTO E-232 — PROCEDIMIENTO DE GESTIÓN DE CERTIFICADOS DIGITALES

**Es el procedimiento operativo que materializa la Política de Cifrado y Gestión de Claves ({{ proyecto.codigo_documento_base }}-107) y la Política de Gestión de Claves Criptográficas ({{ proyecto.codigo_documento_base }}-120) en lo relativo a certificados X.509.** Define el ciclo de vida completo de los certificados utilizados por {{ cliente.razon_social }}: emisión, distribución, custodia, rotación y revocación.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-232"
titulo: "Procedimiento de Gestión de Certificados Digitales"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-107, {{ proyecto.codigo_documento_base }}-120"
medidas_ens: ["mp.info.3", "mp.info.4", "mp.com.2"]
---

# PROCEDIMIENTO DE GESTIÓN DE CERTIFICADOS DIGITALES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-232 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para gestionar el ciclo de vida completo de los certificados digitales X.509 utilizados por {{ cliente.razon_social }}, garantizando confidencialidad, autenticidad e integridad en las comunicaciones y operaciones que dependen de ellos, así como la disponibilidad continua mediante la prevención de caducidades.

Este procedimiento desarrolla las medidas **mp.info.3 (cifrado), mp.info.4 (firma electrónica) y mp.com.2 (protección de la confidencialidad)** del Anexo II del Real Decreto 311/2022, alineado con la guía **CCN-STIC 807 (criptología en el ENS)** y con el Reglamento (UE) 910/2014 (eIDAS) en lo aplicable.

## 2. ALCANCE

Aplica a:

- Certificados de servidor TLS para servicios públicos e internos.
- Certificados cliente para autenticación mutua (mTLS).
- Certificados de firma de código, firma de documentos y firma electrónica avanzada/cualificada.
- Certificados de máquina y de servicio para integraciones automáticas.
- Certificados de cifrado y firma de correo (S/MIME).
- Certificados de IoT y dispositivos de red corporativos.

Quedan excluidas las claves criptográficas simétricas y las claves de cifrado de datos en reposo, gestionadas por {{ proyecto.codigo_documento_base }}-120.

## 3. AUTORIDADES DE CERTIFICACIÓN APROBADAS

| Tipo de uso | Autoridades aprobadas |
|---|---|
| **TLS público** | Let's Encrypt, DigiCert, Sectigo, ZeroSSL, otros con OCSP/CRL operativos |
| **TLS interno / mTLS** | PKI corporativa interna (smallstep, Vault PKI, Microsoft AD CS) |
| **Firma electrónica cualificada** | Prestadores cualificados de la lista TSL española (FNMT-RCM, ANCERT, Camerfirma, Uanataca, Firmaprofesional...) |
| **Firma de código** | DigiCert, Sectigo, GlobalSign |
| **Firma de documentos** | Conforme a eIDAS y al uso previsto (avanzada/cualificada) |

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA:** los certificados de firma cualificada utilizan obligatoriamente prestadores cualificados de la lista TSL española y QSCD (qualified signature creation devices). Las claves privadas sensibles se generan y custodian en HSM nivel **FIPS 140-2 Level 3** o superior.
{% endif %}

## 4. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **Responsable de la Seguridad** | Aprobar la PKI y los proveedores, establecer políticas de algoritmos, custodiar credenciales de la CA. |
| **Administrador PKI / Crypto Officer** | Operar la CA interna, emitir certificados, gestionar HSM. |
| **Solicitantes** (propietarios de servicio) | Solicitar certificados con las características adecuadas. |
| **Equipo de Operaciones** | Instalar y rotar certificados en sistemas, suscribirse a alertas de caducidad. |
| **DPO** | Validar certificados que tratan datos personales (firma documental, S/MIME). |

## 5. ALGORITMOS Y LONGITUDES MÍNIMAS APROBADAS

Conforme a la guía CCN-STIC 807 vigente:

| Uso | Algoritmo aprobado | Longitud mínima |
|---|---|---|
| RSA | RSA-2048 mínimo | 2048 bits (3072 recomendado para nuevos) |
| ECDSA | NIST P-256 / P-384 | 256 bits / 384 bits |
| Hash | SHA-256 mínimo | — (SHA-1 prohibido) |
| Firma cualificada | Conforme al QSCD del prestador | — |

Los certificados con algoritmos o longitudes inferiores se reemplazan en la próxima rotación o de forma anticipada si están en uso productivo.

## 6. CICLO DE VIDA DEL CERTIFICADO

### Fase 1 — Solicitud

1. El propietario de servicio cumplimenta el formulario **F-232 — Solicitud de Certificado** con:
   - Nombre común (CN) y SAN solicitados.
   - Uso previsto (servidor TLS, cliente, firma, etc.).
   - Periodo de validez deseado (máximo 397 días para TLS público, conforme a CA/B Forum).
   - Sistema o servicio donde se instalará.
   - Responsable funcional del servicio.

2. El Administrador PKI valida la coherencia de la solicitud (dominio efectivamente controlado, uso permitido).

### Fase 2 — Generación de claves y emisión

3. **Generación de la clave privada** en el sistema destino o en el HSM corporativo. Para certificados privilegiados (firma cualificada, CA intermedia), generación obligatoria en HSM con backup conforme al procedimiento M-of-N de {{ proyecto.codigo_documento_base }}-120.

4. **Generación del CSR** sin enviar la clave privada a la CA.

5. Emisión por la CA aprobada y descarga del certificado emitido.

6. Almacenamiento en el **inventario centralizado de certificados** (herramienta tipo CertManager, AppViewX, Venafi o similar) con:
   - CN, SAN, fingerprint.
   - Fechas de emisión y caducidad.
   - Sistema o servicio donde se instala.
   - Propietario funcional.
   - Algoritmo y longitud.
   - CA emisora.

### Fase 3 — Distribución e instalación

7. Distribución por canales seguros al sistema destino. La clave privada nunca se envía por correo electrónico, mensajería instantánea o herramientas similares; se utilizan canales cifrados (SSH, SCP, gestor de secretos como HashiCorp Vault, Azure Key Vault, AWS Secrets Manager).

8. Instalación con permisos mínimos: la clave privada solo es accesible por el proceso que la utiliza; en sistemas Linux con permisos 0400 al usuario del servicio.

9. Pruebas post-instalación: verificación con SSL Labs (puntuación A+ mínima en TLS público), curl/openssl en internos, validación funcional del servicio.

### Fase 4 — Operación

10. **Suscripción a alertas de caducidad:** el inventario alerta al propietario funcional y al Administrador PKI con:
    - 60 días antes (informativa).
    - 30 días antes (planificación de rotación).
    - 14 días antes (urgente).
    - 7 días antes (escalado al Responsable de Seguridad).

11. **Rotación regular:** preferencia por automatizar rotaciones cuando sea posible (ACME en Let's Encrypt, integración con cert-manager en Kubernetes, autorrenewal en proveedores cloud).

12. **Reporte mensual** del estado del inventario al Comité de Seguridad: certificados próximos a caducar, certificados con algoritmos a actualizar, certificados huérfanos.

### Fase 5 — Rotación / renovación

13. Generación de **nueva clave privada** en cada rotación (no se reutiliza la anterior).

14. Despliegue progresivo en sistemas con balanceo de carga; verificación de no caída de servicio.

15. Conservación del certificado anterior por 30 días para diagnóstico y rollback, tras lo cual se destruye conforme a {{ proyecto.codigo_documento_base }}-214.

### Fase 6 — Revocación

Procede la revocación inmediata cuando:

- La clave privada se sospecha comprometida.
- El servicio asociado deja de existir.
- Se detecta emisión incorrecta o no autorizada.
- El propietario funcional cesa sin reasignación.

16. Solicitud de revocación a la CA por el canal autorizado (API, panel del proveedor).

17. Verificación de la publicación en CRL/OCSP en menos de 24 horas.

18. Comunicación al SOC para refuerzo de monitorización en caso de revocación por compromiso.

19. Si afectaba a datos personales, evaluación con el DPO de obligaciones de notificación.

## 7. CONTROLES DE LA AUTORIDAD INTERNA (PKI corporativa)

Cuando {{ cliente.razon_social }} opera CA propia:

- **CA raíz offline** custodiada en sala segura con doble llave; activación solo para firmar CAs intermedias.
- **CAs intermedias** operativas con HSM, backup y separación de roles.
- **CRL y OCSP** publicados en endpoint accesible y monitorizado (uptime ≥ 99,9 %).
- **Auditoría anual** de la PKI por tercero independiente (alineada con WebTrust o similar para CAs externas, o según buenas prácticas internas).
- **Plan de renovación** de la jerarquía con antelación mínima de 12 meses respecto a la caducidad de la raíz.

## 8. INTEGRACIÓN CON OTROS PROCEDIMIENTOS

| Procedimiento | Relación |
|---|---|
| {{ proyecto.codigo_documento_base }}-120 (Política de claves) | Define el marco que este procedimiento ejecuta para certificados. |
| {{ proyecto.codigo_documento_base }}-204 (Incidentes) | Compromiso de clave privada se gestiona como incidente. |
| {{ proyecto.codigo_documento_base }}-211 (Cuentas privilegiadas) | Las cuentas de PKI son privilegiadas y siguen su régimen. |
| {{ proyecto.codigo_documento_base }}-218 (Auditoría interna) | El inventario de certificados se audita anualmente. |

## 9. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| F-232 | Solicitud de Certificado | Vigente + 6 años |
| INV-cert | Inventario de Certificados | Permanente |
| L-232 | Logs de la CA y del HSM | 6 años |
| R-232.1 | Reporte mensual de estado | 3 años |
| R-232.2 | Actas de rotación / revocación significativa | 6 años |

## 10. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| Certificados caducados activos | recuento | 0 |
| % rotaciones automatizadas | automáticas / total | ≥ 80 % |
| % certificados conformes con CCN-STIC 807 | conformes / total | 100 % |
| Tiempo medio de revocación tras solicitud | media horas | ≤ 4 |
| Cobertura del inventario | certificados inventariados / detectados (descubrimiento) | ≥ 98 % |

## 11. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Cambien las recomendaciones de algoritmos en CCN-STIC 807.
- Cambie la lista TSL de prestadores cualificados que se utilizan.
- Se modifique la PKI corporativa.
- Aparezcan vulnerabilidades en algoritmos previamente aprobados.
- Se modifique el régimen eIDAS.

Responsabilidad: **Responsable de la Seguridad** + **Administrador PKI**, con aprobación del **Comité de Seguridad**.
