# Registro de cambios / Changelog

Todos los cambios importantes de **ClimaAccesible**.
Lo más reciente, arriba. En español primero y en inglés después.

*All notable changes to **ClimaAccesible**. Newest on top. Spanish first, English below.*

---

## 1.5 — 2026-09-08

### Español

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
