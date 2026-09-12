# ClimaAccesible para NVDA (Accessible Weather)

Autora: Daliana
Versión: 1.6
Compatibilidad: NVDA 2023.1 en adelante
Licencia: GNU GPL v2

[Read in English below](#english-version)

[Registro de cambios](CHANGELOG.md) · [Changelog](CHANGELOG.md)

---

## Versión en Español

ClimaAccesible es un complemento para NVDA pensado para consultar el estado del tiempo y el pronóstico de los próximos días de forma rápida, cómoda y sin complicaciones.

### Ventajas de este complemento
- Funciona de inmediato: Utiliza la API abierta de Open-Meteo. No tienes que entrar a ninguna página web rara a crearte cuentas ni conseguir claves privadas. Lo instalas, eliges tu ciudad y ya funciona.
- Pronóstico fácil de entender: Dice claramente hoy, mañana y los días que siguen (por ejemplo: lunes 7 de septiembre), sin repetir fechas ni mezclar días.
- Avisos de lluvia por momento del día: Si va a llover, te dice si será por la mañana, por la tarde, por la noche o durante todo el día.
- Ciudades sin conexión: Contiene una lista de más de 50.000 localidades organizadas por País, Provincia o Departamento y Ciudad, para que elijas la tuya sin necesidad de GPS ni permisos especiales.
- Elige qué quieres escuchar: Desde las opciones puedes marcar o desmarcar con casillas si quieres saber la sensación térmica, humedad, viento, presión, índice UV o la hora en que sale y se pone el sol.

### Atajos de teclado
- NVDA + W: Escuchar el clima actual en tu ciudad.
- NVDA + Shift + W: Escuchar el pronóstico para los próximos días.
- NVDA + Control + W: Abrir la ventana de configuración para elegir tu ciudad o cambiar las opciones.

### Menú en Herramientas de NVDA
También puedes acceder desde el menú de NVDA > Herramientas > ClimaAccesible:
- Configuración del complemento: Abre la ventana de opciones.
- Comprobar conflictos con otros complementos...: Verifica si otros complementos interfieren con los atajos.
- Documentación: Abre este manual de ayuda.

### Cómo empezar
1. Presiona NVDA + Control + W para abrir las opciones.
2. En la lista País, selecciona tu país.
3. Con Tabulador pasa a Región / Departamento y elige el tuyo.
4. Con Tabulador pasa a Ciudad y elige tu localidad.
5. Marca las casillas de los datos que te interesen y pulsa Guardar.

## Novedades de la versión 1.6 (12 de septiembre de 2026)

### Mejorado

- Al desactivar o recargar complementos, los elementos del menú Herramientas se destruyen adecuadamente liberando recursos de la interfaz.
- La opción de menú para abrir la documentación detecta automáticamente el idioma de NVDA y abre la versión correspondiente en español o inglés.
- La ventana de configuración añade identificadores estándar de wxWidgets para aceptar y cancelar, permitiendo cerrar directamente con Escape o guardar con Intro, además de atajos mnemónicos en los botones.

---

## Novedades de la versión 1.5 (8 de septiembre de 2026)

### Corregido

- No se podía guardar la configuración: se usaba un dato que no existía y la operación fallaba.
- El pronóstico de los próximos días se leía siempre en español, aunque NVDA estuviera en otro idioma. Ahora se traduce como el resto.
- Unas 45 frases del vocabulario meteorológico (direcciones del viento, estados del cielo, momentos del día) no estaban preparadas para traducirse. Ya lo están, y se tradujeron al inglés.
- Varios nombres técnicos del servicio meteorológico aparecían por error como texto traducible.

### Cambios internos

- La consulta del tiempo actual y la del pronóstico se repartieron en piezas con nombre: armar la petición, interpretar la respuesta y redactar cada frase.
- La parte que decide cómo se cuenta la lluvia de cada día quedó separada y con pruebas propias.
- Los textos añadidos se pasaron al español neutro del resto del complemento.
- Se añadieron 43 comprobaciones automáticas que se ejecutan solas en GitHub con cada cambio.

El listado completo de todas las versiones está en el archivo CHANGELOG.md
del repositorio del complemento.

### Créditos y Agradecimientos
- Idea original: Inspirado en el concepto pionero de Weather Plus creado por Adriano Barbieri y colaboradores. ClimaAccesible fue reescrito desde cero para funcionar con Open-Meteo sin claves API, con fechas naturales en español y base de ciudades local.
- Datos del clima: Provistos por Open-Meteo bajo licencia Creative Commons Atribución 4.0 (CC BY 4.0).
