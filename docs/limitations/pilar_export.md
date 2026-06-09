# Limitacion: Exportacion a formato PILAR real

## Estado actual
FULKRO genera exportacion XML nativa (`/analyses/{id}/export-xml`) que
contiene todos los datos del analisis MAGERIT en formato estructurado
propio. **NO es formato PILAR .mgr real**.

## Razon de la limitacion
El formato `.mgr` utilizado por PILAR (herramienta oficial del CCN para
analisis de riesgos MAGERIT) es **propietario y no esta documentado
publicamente**. No existe XSD oficial ni especificacion publica del
formato.

El spec del proyecto FULKRO lo confirma: *"PILAR a dia de hoy NO tiene
API publica; se trabaja con ficheros propios .mgr"*.

## Impacto para el cliente

**Lo que SI funciona:**
- Exportacion XML completa de todos los datos del analisis
- Backup y archivado del analisis
- Intercambio entre instancias FULKRO
- Base para conversion manual a formato PILAR

**Lo que NO funciona:**
- Importacion directa automatizada en PILAR oficial
- Ciclo cerrado PILAR -> FULKRO -> PILAR sin intervencion manual

## Via de resolucion futura

1. **XSD oficial del formato .mgr** publicado por el CCN
2. **Ejemplo real de fichero .mgr** exportado por PILAR oficial
3. **Contacto directo con el equipo CCN PILAR**

## Alternativa practica para consultores FULKRO

1. Ejecutar el analisis completo en FULKRO
2. Exportar el informe PDF firmado (`/report.pdf`)
3. Si el auditor exige fichero PILAR, usar el XML como referencia
   para recrear manualmente en PILAR oficial

## TODO futuro
Ver TODO-9 y TODO-24 en `progress/todos.md`.
