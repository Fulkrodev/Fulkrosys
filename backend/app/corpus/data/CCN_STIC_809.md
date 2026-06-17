# CCN-STIC-809 — Declaración, Certificación y Aprobación Provisional de conformidad con el ENS y Distintivos de cumplimiento

Guía de Seguridad de las TIC · Centro Criptológico Nacional · Abril 2026.

## 1. Introducción

El Real Decreto 311/2022, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad (ENS) en cumplimiento del artículo 156 de la Ley 40/2015, regula la seguridad de los sistemas de información de las entidades del Sector Público: el conjunto de principios básicos y requisitos mínimos para una protección adecuada de la información tratada y los servicios prestados.

Fortalecer la ciberseguridad demanda recursos económicos, humanos y tecnológicos dimensionados según el principio de proporcionalidad y el nivel de seguridad requerido, con una dinámica de mejora continua adaptativa. Las normas de conformidad se concretan en cuatro: Administración Digital, ciclo de vida de servicios y sistemas, mecanismos de control y procedimientos de determinación de la conformidad con el ENS.

Es responsabilidad de las organizaciones que el esfuerzo desarrollado en pos de un desenvolvimiento seguro de sus sistemas de información se publicite adecuadamente, trasladando a los ciudadanos la confianza de que se hallan ante servicios públicos eficaces y seguros.

### Artículo 38 del ENS — Procedimientos de determinación de la conformidad

1. Los sistemas de información del ámbito del artículo 2 serán objeto de un proceso para determinar su conformidad con el ENS. Los sistemas de categoría MEDIA o ALTA precisarán de una auditoría para la certificación de su conformidad, sin perjuicio de la auditoría de seguridad del artículo 31 que podrá servir asimismo para la certificación; los sistemas de categoría BÁSICA solo requerirán de una autoevaluación para su declaración de conformidad, sin perjuicio de que puedan someterse igualmente a una auditoría de certificación. Tanto la autoevaluación como la auditoría de certificación se realizarán según el artículo 31 y el anexo III y en los términos de la correspondiente Instrucción Técnica de Seguridad.

2. Los sujetos responsables darán publicidad, en los correspondientes portales de internet o sedes electrónicas, a las declaraciones y certificaciones de conformidad con el ENS.

La presente Guía articula el mecanismo de Declaración y Certificación de Conformidad con el ENS e introduce el concepto de Aprobación Provisional de Conformidad (APC), descrito en la Guía CCN-CERT IC-01/19 ENS: Criterios Generales de Auditoría y Certificación.

## 2. La conformidad con el Esquema Nacional de Seguridad

### 2.1. Criterios de determinación de la conformidad

El RD 311/2022 aplica a los sistemas de información de todo el sector público (artículo 2 Ley 40/2015), incluyendo los sistemas de las entidades públicas o privadas que formen parte de la cadena de suministro en la prestación de servicios competenciales a las organizaciones públicas, en la medida que lo determine un previo análisis de riesgos.

La conformidad con el ENS se alcanza satisfaciendo los mandatos de su texto articulado y mediante la adecuada implantación de las medidas de seguridad del Anexo II, previa categorización de los sistemas a proteger. Las Guías CCN-STIC 802 (auditoría), 804 (implantación) y 808 (verificación del cumplimiento de las medidas) proporcionan los criterios de determinación de la conformidad, implantación y verificación.

La determinación de la conformidad de sistemas de categoría MEDIA o ALTA se realiza mediante un procedimiento de auditoría formal que, con carácter ordinario, verifique el cumplimiento al menos cada dos (2) años. Con carácter extraordinario, deberá realizarse siempre que se produzcan modificaciones sustanciales que puedan repercutir en las medidas de seguridad requeridas (artículo 31 y Anexo III).

La organización titular deberá contar con procedimientos que permitan detectar dichas modificaciones y comunicarlas a la Entidad de Certificación (EC) o al Órgano de Auditoría Técnica del Sector Público (OAT). La ausencia de tal comunicación, cuando fuere necesaria, podrá suponer la retirada de la Certificación de Conformidad concedida.

Para la categoría BÁSICA basta con un procedimiento de autoevaluación que, con carácter ordinario, verifique el cumplimiento al menos cada dos (2) años, y con carácter extraordinario ante modificaciones sustanciales. El plazo de dos años podrá extenderse tres (3) meses por fuerza mayor no imputable a la organización. Nada impide que un sistema BÁSICA se someta igualmente a una auditoría formal, siendo esta posibilidad siempre la deseable.

Un sistema de categoría MEDIA o ALTA requiere disponer de un SGSI para la gestión de su seguridad (medida [op.pl.2] arquitectura de seguridad), basado en mejora continua (ciclo de Deming PDCA). El objetivo de la auditoría de certificación del ENS es aportar la confianza de que el sistema ha sido auditado por un tercero independiente, imparcial y capacitado.

### 2.2. Procedimiento de determinación de la conformidad

La conformidad de un sistema concreto pasa por adoptar y manifestar que se han implementado las medidas de seguridad requeridas para tal sistema según su categoría (BÁSICA, MEDIA o ALTA), asegurando que tales medidas se mantienen a lo largo de todo el ciclo de vida del sistema.

#### Artículo 31 del ENS — Auditoría de la seguridad

1. Los sistemas serán objeto de una auditoría regular ordinaria, al menos cada dos años, que verifique el cumplimiento de los requerimientos del ENS. Con carácter extraordinario, deberá realizarse siempre que se produzcan modificaciones sustanciales; la auditoría extraordinaria determina la fecha de cómputo para el cálculo de los dos años de la siguiente ordinaria. El plazo de dos años podrá extenderse tres meses por fuerza mayor.

2. La auditoría se realizará en función de la categoría del sistema y, en su caso, del perfil de cumplimiento específico, según los anexos I y III y la Instrucción Técnica de Seguridad de Auditoría.

4. El informe de auditoría deberá dictaminar sobre el grado de cumplimiento del real decreto identificando los hallazgos de cumplimiento e incumplimiento, los criterios metodológicos, el alcance y el objetivo de la auditoría, y los datos, hechos y observaciones en que se basen las conclusiones.

5. Los informes de auditoría se presentarán al responsable del sistema y al responsable de la seguridad; este último los analiza y presenta sus conclusiones al responsable del sistema para que adopte las medidas correctoras adecuadas.

6. En sistemas de categoría ALTA, visto el dictamen y la eventual gravedad de las deficiencias, el responsable del sistema podrá suspender temporalmente el tratamiento de informaciones, la prestación de servicios o la operación del sistema hasta su adecuada subsanación o mitigación.

### Cuadro resumen Anexo III — procedimientos de determinación de la conformidad

- AUTOEVALUACIÓN (categoría BÁSICA → DECLARACIÓN DE CONFORMIDAD): realizada por el mismo personal que administra el sistema o aquel en quien hubiere delegado. Documento de autoevaluación indicando si cada medida de seguridad está implementada y sujeta a revisión regular, y las evidencias que sustentan la valoración. Los documentos de autoevaluación serán analizados por el responsable de seguridad competente, que elevará las conclusiones al responsable del sistema.

- AUDITORÍA FORMAL (categoría MEDIA / ALTA → CERTIFICACIÓN DE CONFORMIDAD): realizada con garantías metodológicas, de independencia, profesionalidad e imparcialidad. Informe de auditoría que califica las desviaciones distinguiendo entre No Conformidades Mayores, No Conformidades Menores y Observaciones, y podrá contener oportunidades de mejora. Los informes serán analizados por el responsable de seguridad competente, que presentará sus conclusiones al responsable del sistema.

## 3. Publicidad de la conformidad

### 3.1. Esquema de declaración y certificación de la conformidad

La exhibición de una Declaración de Conformidad (obligatoria para categoría BÁSICA) o una Certificación de Conformidad (obligatoria para MEDIA o ALTA, voluntaria para BÁSICA), y en su caso sus distintivos, son necesarios para mostrar el compromiso de la entidad con la seguridad de los sistemas.

En comunidades autónomas con lengua cooficial se podrán expedir las declaraciones, certificaciones y distintivos en castellano o en texto bilingüe.

Para sistemas de categoría MEDIA o ALTA, el Centro Criptológico Nacional (CCN) y la Entidad Nacional de Acreditación (ENAC) participan en la acreditación de las Entidades de Certificación del ENS. La Certificación de Conformidad podrá ser expedida por una Entidad de Certificación acreditada por ENAC conforme a UNE-EN ISO/IEC 17065:2012 para la certificación de sistemas del ámbito del ENS.

La Entidad de Certificación (ni la entidad legal a la que pertenezca ni entidades bajo su control) no podrá ofrecer consultoría o asistencia en SGSI, gobierno de la seguridad, metodologías o herramientas asociadas (ENS, ISO 27001, COBIT, Octave, MAGERIT, PILAR…) ni auditorías internas sobre tales referentes; ni podrá certificar a una organización si en los dos años anteriores le hubiese prestado servicios cuyo resultado deba usarse en el proceso de certificación (análisis de riesgos, diseño o implantación de controles o continuidad). Esta separación consultor/certificador es regla de imparcialidad.

El CCN mantendrá en su sede electrónica una relación actualizada de las Entidades de Certificación (EC) acreditadas o en vías de acreditación y de los Órganos de Auditoría Técnica (OAT) reconocidos. Los certificados caducados se mantienen publicados dos (2) meses salvo excepción justificada.

### 3.2. Declaración de conformidad (categoría BÁSICA)

Cuando se trate de sistemas de categoría BÁSICA, el titular del órgano superior dará publicidad a la conformidad mediante una Declaración de Conformidad (estructura y contenido en el Anexo A de la Guía). Se expresará en un documento electrónico, en formato no editable, firmado electrónicamente por la propia organización bajo cuya responsabilidad se encuentre el sistema o por quien hubiere delegado.

La Declaración podrá representarse mediante un Sello o Distintivo de Declaración de Conformidad, publicitado por la organización titular empleando siempre los modelos de sellos/distintivos diseñados por el CCN y descargables de su web. El distintivo será un documento electrónico no editable que incluirá un enlace a la Declaración de Conformidad, accesible en la sede electrónica o web de la organización.

### 3.3. Certificación de conformidad (categoría MEDIA o ALTA)

Cuando se trate de sistemas de categorías MEDIA o ALTA, el sistema deberá superar la correspondiente Auditoría (Anexo III). El titular del órgano superior dará publicidad mediante la exhibición de una Certificación de Conformidad, expresada en documento electrónico no editable firmado electrónicamente por la Entidad Certificadora, conteniendo al menos la información de la ITS de conformidad (ejemplo en el Anexo B).

La Certificación podrá representarse mediante un Sello o Distintivo de Certificación de Conformidad expedido por la Entidad Certificadora, empleando los modelos del CCN, condicionado a la posesión de la Certificación. El distintivo incluirá un enlace a la Certificación, accesible en la sede electrónica o web de la entidad.

### 3.4. Comunicación de las certificaciones al CCN y su publicación

Las Entidades de Certificación comunicarán al CCN la expedición de los Certificados de Conformidad dentro de los quince (15) días siguientes, a través del servicio web del CCN, adjuntando el documento electrónico de Certificación firmado/sellado. El CCN mantendrá en su web una relación de las organizaciones públicas o privadas certificadas, con los sistemas certificados, los servicios soportados y las fechas de expedición y expiración.

Los Informes de Autoevaluación o Auditoría podrían contener información sensible; la solicitud de tales informes por entidades públicas usuarias de soluciones del sector privado titulares de una Declaración o Certificación se dirige a cocens@ccn.cni.es, que valorará la petición.

## 4. La aprobación provisional de conformidad con el ENS (APC)

Conforme a la Guía CCN-CERT IC-01/19, podrá expedirse excepcionalmente una Aprobación Provisional de Conformidad (APC) para sistemas de categorías BÁSICA o MEDIA. La APC será emitida por el CCN a petición del Órgano de Auditoría Técnica del Sector Público (OAT, regulado en la Guía CCN-STIC 122) o de la Entidad de Certificación.

La APC se expresará en documento electrónico no editable firmado por el CCN (formato en el Anexo C). Podrá representarse mediante un Distintivo de Aprobación Provisional de Conformidad expedido por el CCN, con enlace a la APC accesible en la sede electrónica o web. No se publicitarán en la web del CCN las organizaciones con APC hasta que hayan completado el Plan de Acciones Correctivas resultado de la auditoría y obtenido la Certificación de Conformidad correspondiente.

## 5. Consejo de Certificación del Esquema Nacional de Seguridad (CoCENS)

La expedición de las Certificaciones de Conformidad exige el concurso coordinado de ENAC (acredita a las Entidades de Certificación), el Ministerio de Política Territorial y Función Pública y el CCN (co-responsables del ENS). Las Guías CCN-STIC son "Mejores Prácticas" (soft law): su cumplimiento no es obligatorio, aunque su inobservancia, ante un incidente que ponga en riesgo la seguridad, podría derivar en responsabilidad.

El CoCENS se constituye como órgano colegiado (Ley 40/2015). Lo preside el Director del CCN. Miembros permanentes: Jefe del Área de Normativa y Servicios de Ciberseguridad del CCN, un representante del Ministerio de Política Territorial y Función Pública, y el Director Técnico de ENAC. Miembros no permanentes: un representante de cada OAT o Entidad de Certificación acreditada, y especialistas externos.

Fines del CoCENS: velar por la adecuada implantación de la Certificación del ENS; alentar los procesos de certificación; redactar y publicar Normas, Informes, Criterios o Buenas Prácticas; asesorar sobre métodos, procedimientos, herramientas y criterios; asesorar en el reconocimiento mutuo de certificados; e informar sobre el grado de implantación. Se reunirá como mínimo una vez al año y las decisiones se adoptarán por consenso de sus miembros permanentes.
