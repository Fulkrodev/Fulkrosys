---
codigo_documento: "L-005"
titulo: "Cláusula de Confidencialidad de la Información de la Administración Pública (Artículo 133 LCSP)"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "CONFIDENCIAL · cláusula adjunta a contratos AAPP"
norma_aplicable: "Ley 9/2017 LCSP · Art. 133"
---

# CLÁUSULA DE CONFIDENCIALIDAD DE LA INFORMACIÓN DE LA ADMINISTRACIÓN CONTRATANTE

*(Cláusula tipo para incorporación en contratos celebrados con entidades del sector público, en cumplimiento del artículo 133 de la Ley 9/2017 LCSP)*

---

{% set contrato_ref = contrato.referencia if contrato and contrato.referencia else '[REFERENCIA CONTRATO PRINCIPAL]' %}
{% set organo_contratante = licitacion.organo_contratante if licitacion and licitacion.organo_contratante else '[ÓRGANO DE CONTRATACIÓN]' %}

## CLÁUSULA — CONFIDENCIALIDAD

**1. Alcance del deber de confidencialidad.**

{{ cliente.razon_social }} (en adelante, "el Contratista") se obliga a tratar como **confidencial** toda la información o datos a los que tenga acceso en el desempeño del contrato {{ contrato_ref }} celebrado con {{ organo_contratante }} (en adelante, "la Administración"), incluyendo, con carácter no limitativo:

a) Información expresamente designada como confidencial por la Administración.

b) Datos personales y datos especialmente protegidos que tengan tal consideración conforme al RGPD y a la LOPDGDD.

c) Información técnica, organizativa, comercial, económica o estratégica de la Administración o de terceros que el Contratista conozca como consecuencia de la ejecución del contrato.

d) Información sobre sistemas, infraestructuras, vulnerabilidades, configuraciones, planos, esquemas, claves o credenciales que afecten a la seguridad de los sistemas y servicios de la Administración.

e) Cualquier otra información que, por su naturaleza, deba ser razonablemente considerada como reservada o sensible.

**2. Personal del Contratista.**

El Contratista se obliga a:

a) Limitar el acceso a la información confidencial al personal **estrictamente necesario** para la ejecución del contrato.

b) Suscribir con dicho personal **compromisos individuales de confidencialidad** con contenido equivalente al de la presente cláusula.

c) Adoptar medidas técnicas y organizativas razonables para impedir la divulgación de la información a personas no autorizadas.

d) Formar y sensibilizar al personal asignado sobre el alcance y consecuencias del deber de confidencialidad.

**3. Subcontratistas.**

En caso de que se autorice la subcontratación de parte de las prestaciones, el Contratista quedará obligado a:

a) Imponer al subcontratista el mismo deber de confidencialidad y bajo las mismas condiciones que se establecen en la presente cláusula.

b) Responder ante la Administración del cumplimiento del deber de confidencialidad por parte del subcontratista.

**4. Prohibición de uso para fines distintos.**

El Contratista no podrá:

a) Utilizar la información confidencial para fines distintos de los específicamente necesarios para la ejecución del contrato.

b) Divulgar, ceder, distribuir o de cualquier otra forma poner la información confidencial a disposición de terceros sin autorización **expresa, previa y por escrito** de la Administración.

c) Conservar la información confidencial más allá del plazo estrictamente necesario para la ejecución del contrato y, en cualquier caso, una vez extinguido este.

**5. Excepciones al deber de confidencialidad.**

No se considerará incumplimiento del deber de confidencialidad la comunicación de información que:

a) Sea o llegue a ser de dominio público sin culpa del Contratista.

b) Fuera ya conocida por el Contratista antes de su recepción, debiendo poderlo acreditar fehacientemente.

c) Fuera obtenida lícitamente de un tercero sin obligación de confidencialidad.

d) Deba ser comunicada en cumplimiento de una obligación legal o de un requerimiento de autoridad competente, en cuyo caso el Contratista lo notificará a la Administración de forma previa siempre que sea legalmente posible.

**6. Duración del deber de confidencialidad.**

El deber de confidencialidad subsistirá:

a) Durante toda la vigencia del contrato {{ contrato_ref }}, incluyendo prórrogas.

b) Durante un período mínimo de **cinco (5) años** desde la extinción del contrato por cualquier causa, conforme al artículo 133.2 LCSP, sin perjuicio de la duración superior que la naturaleza de determinada información pudiera exigir.

c) Indefinidamente cuando la información tenga la consideración de **clasificada** conforme a la legislación aplicable o de **secreto comercial** legalmente protegido.

**7. Devolución y destrucción de la información.**

Al término del contrato, el Contratista procederá, conforme a las instrucciones recibidas de la Administración, a:

a) **Devolver** los soportes, documentación e información a los que haya tenido acceso, o

b) **Destruir de forma segura** dicha información, aportando certificación documental del destino dado a la misma en plazo máximo de **treinta (30) días naturales** desde la solicitud, incluyendo la información obrante en copias de seguridad y sistemas auxiliares.

**8. Incumplimiento del deber de confidencialidad.**

El incumplimiento del presente deber de confidencialidad por parte del Contratista o de su personal:

a) Tendrá la consideración de **incumplimiento esencial** del contrato y podrá ser causa de su resolución conforme al artículo 211 LCSP.

b) Generará la obligación del Contratista de indemnizar a la Administración por los daños y perjuicios efectivamente causados.

c) Podrá determinar la imposición de **prohibición de contratar** conforme al artículo 71 LCSP cuando concurran los presupuestos legales.

d) Será comunicado al Ministerio Fiscal cuando los hechos pudieran ser constitutivos de infracción penal.

**9. Protección de datos personales.**

Cuando la información confidencial incluya datos personales, el tratamiento se ajustará adicionalmente a lo dispuesto en el RGPD, en la LOPDGDD y, en su caso, en el contrato de encargo de tratamiento suscrito entre las partes como anexo al contrato principal.

---

*Documento L-005 · Cláusula confidencialidad información AAPP Art. 133 LCSP · {{ cliente.razon_social }} · Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}*
