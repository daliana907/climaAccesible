# Accessible Weather (ClimaAccesible) for NVDA

* **Author:** Daliana
* **Version:** 1.4
* **Compatibility:** NVDA 2019.3 or later
* **License:** GNU General Public License v2.0 (GPLv2)

[Versión en español más abajo](#versión-en-español)

---

## English

**Accessible Weather (ClimaAccesible)** is an accessible weather and forecast add-on for the NVDA screen reader. It allows users to check current weather conditions and detailed multi-day forecasts using simple, accessible keyboard shortcuts.

### Why ClimaAccesible?
Unlike legacy weather add-ons that require obtaining private API keys from commercial services, suffer from confusing date formatting in non-English languages, or bundle heavy legacy libraries, ClimaAccesible was built from scratch to provide a seamless, modern experience:

* **Zero configuration & no API keys:** Powered by the open Open-Meteo API. It requires no registration, no accounts, and no API keys. It works right out of the box upon installation.
* **Natural language forecast:** Features a human-friendly forecasting engine that clearly announces "today", "tomorrow", and subsequent calendar dates ("Monday, September 7"), avoiding confusing repetitive dates.
* **Time-of-day rain breakdown:** Announces whether precipitation is expected in the morning, afternoon, evening, or throughout the day.
* **Offline geographic database:** Includes an offline database (`geodata.json`) with over 50,000 cities organized into accessible cascading dropdowns (Country > Region > City), with no GPS tracking or location permissions needed.
* **20 customizable weather metrics:** Users can toggle exactly which metrics they wish to hear (temperature, apparent sensation, humidity, wind speed/gusts/direction, atmospheric pressure, UV index, sunrise/sunset, daylight hours, etc.).

### Keyboard Shortcuts
* **NVDA + W**: Announces current weather conditions for the configured city.
* **NVDA + Shift + W**: Announces the multi-day extended weather forecast.
* **NVDA + Control + W**: Opens the accessible settings dialog to choose your city and customize announced metrics.

### Third-Party Data & Privacy
* Weather forecasts and meteorological data are provided by [Open-Meteo](https://open-meteo.com/) under the [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) license.
* The add-on respects user privacy: it transmits only geographical coordinates (latitude and longitude) to fetch public meteorological data, without gathering or storing any personal identifiers or location history.

### Credits & License
* **Author:** Daliana
* **License:** GNU General Public License v2.0 (GPLv2)

---

## Versión en Español

**ClimaAccesible** es un complemento de información meteorológica y pronóstico del tiempo para el lector de pantalla NVDA. Permite consultar el clima actual y el pronóstico de los próximos días mediante atajos de teclado accesibles.

### Características Principales
* **Sin cuentas ni claves API:** Funciona de forma inmediata gracias a la API abierta de Open-Meteo, sin necesidad de registros externos ni claves privadas.
* **Pronóstico con lenguaje natural:** Distingue con total claridad entre «hoy», «mañana» y las fechas posteriores («lunes 7 de septiembre»), sin mezclar días.
* **Precipitaciones por franja horaria:** Informa si las lluvias ocurrirán por la mañana, por la tarde, por la noche o durante todo el día.
* **Base de datos de ciudades sin conexión:** Más de 50.000 localidades organizadas en listas desplegables (País > Departamento/Región > Ciudad) sin requerir GPS.
* **20 opciones personalizables:** Permite elegir con casillas de verificación qué datos escuchar (temperatura, sensación térmica, humedad, viento, ráfagas, presión, índice UV, horas de luz, etc.).

### Atajos de Teclado
* **NVDA + W**: Anuncia el clima actual de la ciudad configurada.
* **NVDA + Shift + W**: Anuncia el pronóstico del tiempo para los próximos días.
* **NVDA + Control + W**: Abre la ventana de configuración.

### Datos de Terceros y Privacidad
* Datos meteorológicos proporcionados por [Open-Meteo](https://open-meteo.com/) bajo licencia [Creative Commons Atribución 4.0 Internacional (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
* El complemento no recopila datos personales ni requiere permisos de rastreo.
