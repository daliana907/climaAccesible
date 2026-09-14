# Registro de cambios / Changelog

Todos los cambios importantes de **ClimaAccesible**.
Lo más reciente, arriba. En español primero y en inglés después.

*All notable changes to **ClimaAccesible**. Newest on top. Spanish first, English below.*

---

## 1.8 — 2026-09-13

### Español

- Descarte de horas pasadas en predicción de lluvia de hoy: se incorporó un filtro temporal que compara la hora actual de la ciudad con las marcas horarias de precipitación, impidiendo que una consulta realizada en la tarde o en la noche verbalice probabilidades máximas o periodos de lluvia que ya sucedieron (como la madrugada).
- Corrección de condición meteorológica y descarte de probabilidades residuales de lluvia en el pronóstico de hoy: al consultar el pronóstico extendido (NVDA+Shift+W), el estado del tiempo para el día actual utilizaba el código diario agregado de 24 horas de Open-Meteo, lo que causaba que una llovizna ocurrida en la madrugada se siguiera anunciando como estado del día por la tarde. Ahora se evalúan los códigos meteorológicos de las horas restantes junto a la condición actual para reflejar fielmente cómo estará el resto de la jornada. Asimismo, se incorporó un filtro que descarta probabilidades residuales inferiores al 15% cuando no hay acumulación de lluvia prevista (0.0 mm), evitando anuncios innecesarios de lluvia.
- Corrección de desfase horario en predicción de lluvia por franjas: al consultar localidades en husos horarios diferentes al del equipo local, la correspondencia entre los arrays horarios de Open-Meteo (hourly.time, precipitation_probability y precipitation) y la fecha de la ciudad se desalineaba. Se introdujo una correlación temporal estricta evaluando las 24 horas exactas de la ciudad consultada para determinar con certeza si lloverá por la mañana, por la tarde o por la noche.
- Pronunciación en lenguaje natural de horas de luz solar: ajuste en el formato de duraciones para evitar discordancias gramaticales, empleando expresiones naturales en singular y plural ("1 hora y 1 minuto").
- Sanitización y normalización estricta de coordenadas: normalización automática de separadores decimales (sustituyendo comas por puntos) y eliminación de espacios en blanco en latitud y longitud dentro de ConfigDialog para prevenir peticiones HTTP malformadas.
- Detección de portales cautivos y respuestas de red no válidas: detección temprana de páginas HTML de autenticación Wi-Fi o respuestas de error de proxies, con reintento automático y mensajes descriptivos para el usuario en lugar de excepciones de decodificación JSON.
- Prevención de peticiones concurrentes duplicadas: mecanismo de semáforo que descarta pulsaciones repetidas de los atajos NVDA+W y NVDA+Shift+W mientras una consulta meteorológica previa sigue en curso.
- Guardado atómico de configuración: escritura en archivo temporal seguida de reemplazo atómico para proteger config.json contra pérdidas de datos por cortes de energía o reinicios forzados.
- Cierre seguro del diálogo de opciones: detención garantizada de los temporizadores de progreso (wx.Timer) y cancelación de subprocesos antes de cerrar la ventana modal (EndModal), evitando bloqueos en la interfaz gráfica.
- Soporte ampliado de códigos meteorológicos WMO: inclusión de descripciones traducidas para llovizna engelante, chubascos de nieve y granizo.
- Auditoría de conflictos adaptada a distribuciones de teclado: detección de atajos coincidentes compatible con esquemas de teclado para ordenadores portátiles y de sobremesa.

### English

- Elapsed hours filtering for today's precipitation: compares the current local time of the queried city against hourly precipitation timestamps, preventing afternoon or evening queries from reporting past rain intervals (such as dawn or early morning).
- Current-day forecast condition and residual rain filtering: when checking the multi-day forecast (NVDA+Shift+W), today's weather condition previously relied on Open-Meteo's 24-hour daily aggregate code, causing morning drizzle to persist as the announced condition later in the day even when skies cleared. The add-on now evaluates the weather codes of remaining hours alongside the current condition. In addition, residual precipitation probabilities below 15% without measurable accumulation (0.0 mm) are now filtered out, preventing misleading rain announcements.
- Timezone-aware rain interval calculation: fixed an issue where querying locations in differing time zones misaligned Open-Meteo's hourly precipitation arrays with the local calendar day. An explicit local-day timeline correlation now reliably detects whether precipitation falls in the morning, afternoon, or evening.
- Natural language sunlight duration phrasing: improved duration formatting to enforce proper singular and plural agreement (e.g. "1 hour and 1 minute" instead of numeric artifacts).
- Coordinate sanitization and validation: automatic comma-to-dot decimal normalization and whitespace trimming for latitude and longitude in ConfigDialog, preventing malformed HTTP requests.
- Captive portal and invalid network payload handling: early detection of HTML redirect pages from public Wi-Fi logins or proxy errors, featuring automatic retries and descriptive user feedback instead of raw JSON decoding crashes.
- Concurrent query deduplication: state guards ignore repeated presses of NVDA+W or NVDA+Shift+W while a previous network request is already in flight.
- Atomic configuration writes: settings (config.json) are written to a temporary file before atomic replacement, safeguarding user preferences against abrupt power loss.
- Safe settings dialog termination: guaranteed stoppage of progress timers (wx.Timer) and worker threads prior to EndModal disposal, preventing GUI hangs.
- Expanded WMO weather code coverage: added translated descriptions for freezing drizzle, snow showers, and hail.
- Layout-aware gesture conflict auditing: conflict auditor now evaluates keyboard gestures accurately across both desktop and laptop keyboard configurations.

---

## 1.8.1 — 2026-09-13

### Español

Mantenimiento y optimización interna del código. Sin cambios en el funcionamiento del complemento.

Refactorización y unificación de la lógica de peticiones HTTP: se crearon los métodos auxiliares `_normalizarCoord` y `_manejarErrorPeticion`, eliminando más de 40 líneas de código duplicado entre la consulta del tiempo actual (`_fetchWeather`) y el pronóstico extendido (`_fetchForecast`). Se completó además la cobertura total de documentación técnica interna (docstrings) en todas las funciones y clases del complemento.

### English

Internal code maintenance and optimization. No behavioral changes.

Refactored and unified HTTP request handling: introduced helper methods `_normalizarCoord` and `_manejarErrorPeticion`, eliminating over 40 lines of duplicate logic between current weather querying (`_fetchWeather`) and multi-day forecast processing (`_fetchForecast`). Completed 100% technical docstring coverage across all internal functions and classes.

---

## 1.6 — 2026-09-12

### Español

- Descarte de horas pasadas en predicción de lluvia de hoy: se incorporó un filtro temporal que compara la hora actual de la ciudad con las marcas horarias de precipitación, impidiendo que una consulta realizada en la tarde o en la noche verbalice probabilidades máximas o periodos de lluvia que ya sucedieron (como la madrugada).
#### Mejorado

- Al desactivar o recargar complementos, los elementos del menú Herramientas se destruyen adecuadamente liberando recursos de la interfaz.
- El acceso a la documentación desde el menú ahora detecta el idioma activo de NVDA y abre la versión correspondiente en español o inglés.
- La ventana de configuración añade identificadores estándar de wxWidgets para aceptar y cancelar, permitiendo cerrar directamente con Escape o guardar con Intro, además de atajos mnemónicos en los botones.

### English

- Elapsed hours filtering for today's precipitation: compares the current local time of the queried city against hourly precipitation timestamps, preventing afternoon or evening queries from reporting past rain intervals (such as dawn or early morning).
#### Improved

- Clean teardown of Tools menu items on addon termination/reload, preventing orphaned UI handles.
- The documentation menu entry now opens the guide in the user's active NVDA language (Spanish or English).
- The settings dialog now implements standard affirmative and escape IDs (`wx.ID_OK`, `wx.ID_CANCEL`) along with button mnemonics for seamless Enter/Escape keyboard navigation.

---

## 1.5 — 2026-09-08

### Español

- Descarte de horas pasadas en predicción de lluvia de hoy: se incorporó un filtro temporal que compara la hora actual de la ciudad con las marcas horarias de precipitación, impidiendo que una consulta realizada en la tarde o en la noche verbalice probabilidades máximas o periodos de lluvia que ya sucedieron (como la madrugada).
#### Corregido

- No se podía guardar la configuración: se usaba un dato que no existía y la operación fallaba.
- El pronóstico de los próximos días se leía siempre en español, aunque NVDA estuviera en otro idioma. Ahora se traduce como el resto.
- Unas 45 frases del vocabulario meteorológico (direcciones del viento, estados del cielo, momentos del día) no estaban preparadas para traducirse. Ya lo están, y se tradujeron al inglés.
- Varios nombres técnicos del servicio meteorológico aparecían por error como texto traducible.

#### Cambios internos

- La consulta del tiempo actual y la del pronóstico se repartieron en piezas con nombre: armar la petición, interpretar la respuesta y redactar cada frase.
- La parte que decide cómo se cuenta la lluvia de cada día quedó separada y con pruebas propias.
- Los textos añadidos se pasaron al español neutro del resto del complemento.
- Se añadieron 43 comprobaciones automáticas que se ejecutan solas en GitHub con cada cambio.

### English

- Elapsed hours filtering for today's precipitation: compares the current local time of the queried city against hourly precipitation timestamps, preventing afternoon or evening queries from reporting past rain intervals (such as dawn or early morning).
#### Fixed

- Settings could not be saved: the code used a value that did not exist and the operation failed.
- The multi-day forecast was always read in Spanish, even with NVDA in another language. It is now translated like everything else.
- About 45 weather vocabulary phrases (wind directions, sky conditions, times of day) were not translatable. They now are, and were translated into English.
- Several technical names from the weather service were wrongly exposed as translatable text.

#### Internal changes

- The current weather and forecast queries were split into named pieces: build the request, read the answer, write each sentence.
- The part that decides how each day's rain is described is now separate and has its own tests.
- Added texts were reworded into the neutral Spanish used across the add-on.
- Added 43 automatic checks that run on their own on GitHub with every change.

---

## 1.4 y anteriores / 1.4 and earlier

El historial de estas versiones está en los mensajes de guardado del repositorio,
en la pestaña de confirmaciones de GitHub.

*The history of these versions lives in the repository commit messages, on the
GitHub commits tab.*
