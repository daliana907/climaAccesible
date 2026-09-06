# ClimaAccesible para NVDA

* Autora: Daliana
* Versión: 1.3
* Compatibilidad con NVDA: 2019.3 en adelante

ClimaAccesible es un complemento para NVDA que te permite consultar el clima actual, el pronóstico de varios días y configurar tu ciudad, todo mediante atajos de teclado simples. No necesita cuenta ni clave en ningún servicio.

## Atajos de teclado

* **NVDA + W**: Lee el clima actual de tu ciudad configurada
* **NVDA + Shift + W**: Lee el pronóstico de los próximos días (configurable de 1 a 14)
* **NVDA + Control + W**: Abre la ventana de configuración del complemento
* **NVDA + N ➔ Herramientas ➔ ClimaAccesible**: Accede al menú del complemento (Configuración, Comprobar conflictos con otros complementos y Documentación)

## Primeros pasos

La primera vez que instales el complemento, necesitas configurar tu ciudad:

1. Presiona NVDA + Control + W para abrir la configuración.
2. En el combo **País**, elige tu país (los departamentos y ciudades se cargan solos al instante).
3. Con Tab, pasa al combo **Departamento / Región** y elige el tuyo (las ciudades se actualizan solas).
4. Con Tab, pasa al combo **Ciudad** y elige tu localidad.
5. Marca o desmarca las casillas según qué datos quieras escuchar al consultar el clima.
6. En la sección **Pronóstico extendido**, elige cuántos días quieres ver (1 a 14).
7. Presiona **Guardar todo**.

> **Nota:** Los datos de países, departamentos y ciudades están incluidos dentro del complemento (más de 150.000 ciudades). No necesitas Internet para configurar tu ubicación, solo para consultar el clima en tiempo real.

## Clima actual (NVDA + W)

Lee el estado del tiempo en este momento. Puedes elegir exactamente qué datos escuchar desde la configuración:
* Temperatura actual
* Condición del cielo
* Humedad
* Presión atmosférica
* Velocidad y dirección del viento
* Ráfagas
* Horario de salida y puesta del sol

## Pronóstico extendido (NVDA + Shift + W)

Lee el pronóstico para los días venideros. Los datos son altamente personalizables:
* Temperatura máxima y mínima
* Condición principal del día
* Índice UV máximo (útil para protección solar)
* Precipitación esperada (lluvia/nieve)
* Horario de salida y puesta del sol

## Declaración sobre el uso de inteligencia artificial
He utilizado herramientas de inteligencia artificial como ayuda para escribir y organizar el código de este complemento.
Como autora (**Daliana**), he guiado todo el desarrollo, decidido cómo debe funcionar cada característica y probado cada opción paso a paso en mi propio equipo para asegurarme de que funcione bien, sea totalmente accesible con NVDA y no dé errores.

## Uso de servicios y datos de terceros
*En cumplimiento del criterio 1.6 de la Guía de revisión de complementos de NVDA en español:*  
Este complemento hace un uso legítimo y autorizado de servicios de terceros sin recurrir a ingeniería inversa ni claves API no autorizadas:
* Consulta meteorológica mediante la API abierta y documentada de **Open-Meteo**, licenciada bajo **Creative Commons Attribution 4.0 International (CC BY 4.0)**.
* Base de datos geográfica integrada de **Countries States Cities Database**, bajo licencia **Open Database License (ODbL 1.0)**.

## Historial de cambios

### Versión 1.3
* **Auditoría de conflictos**: Nueva opción en el menú de Herramientas para diagnosticar colisiones de atajos de teclado y complementos meteorológicos duplicados.
* **Sistema de registro (log) exhaustivo**: Trazabilidad completa en `nvda.log` con tiempos de respuesta HTTP, códigos de estado, parámetros de consultas y transcripción exacta de cada locución enviada al usuario.
* **Trazas completas de excepciones**: Integración de `exc_info=True` ante posibles errores inesperados o fallos de red.
* **Corrección de importación de red**: Se incluye la importación del módulo `time` a nivel global para el cálculo de latencias y tiempos de respuesta de la API meteorológica, resolviendo el error inesperado al consultar el clima.

### Versión 1.2
* Incorporada la declaración formal de uso de inteligencia artificial (Criterio 4.5) y documentación de servicios de terceros (Criterio 1.6).
* Actualizada la compatibilidad probada con NVDA 2026.2.

### Versión 1.1
* Detección natural de momentos de lluvia y probabilidad máxima diaria de precipitación.
* Extracción automática en cascada de departamentos y ciudades en configuración.
* Corrección de reinicio limpio de NVDA sin hilos residuales.