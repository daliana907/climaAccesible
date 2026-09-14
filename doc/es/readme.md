# ClimaAccesible para NVDA (Accessible Weather)

- Autora: Daliana
- Versión: 1.8
- Compatibilidad: NVDA 2023.1 en adelante
- Licencia: GNU GPL v2

[Read in English](../en/readme.md)

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

### Cómo empezar

1. Presiona NVDA + Control + W para abrir las opciones.
2. En la lista País, selecciona tu país.
3. Con Tabulador pasa a Región / Departamento y elige el tuyo.
4. Con Tabulador pasa a Ciudad y elige tu localidad.
5. Marca las casillas de los datos que te interesen y pulsa Guardar.

---

## Novedades de la versión 1.8.1 (13 de septiembre de 2026)

- Consultas meteorológicas más fiables: se reforzó y unificó la forma en que el complemento se comunica con el servicio de datos del clima, haciendo que tanto la consulta del tiempo actual como la del pronóstico extendido gestionen los errores de conexión de manera más robusta y consistente.
- Limpieza interna y documentación técnica completa de todas las funciones del complemento.

## Novedades de la versión 1.8 (13 de septiembre de 2026)

- Detección inteligente de horas restantes: al consultar el clima actual o el pronóstico para el día de hoy, el complemento descarta automáticamente las horas que ya han transcurrido, asegurando que no se anuncien lluvias o periodos de la madrugada o de la mañana si la consulta se hace por la tarde o por la noche, y adaptando el estado del cielo a las horas restantes del día para no arrastrar lloviznas pasadas cuando solo queda una probabilidad residual.
- Pronóstico de lluvia exacto en cualquier país: al consultar el clima de una ciudad con un huso horario distinto al de tu ordenador, el complemento ahora sincroniza correctamente las horas locales de esa ciudad, diciéndote con exactitud si lloverá por la mañana, por la tarde o por la noche sin desfasarse.
- Anuncio de horas de sol en lenguaje natural: la duración de la luz solar ahora se escucha de forma natural y gramaticalmente correcta en singular y plural (por ejemplo: "1 hora y 1 minuto").
- Escritura de coordenadas más flexible: en la ventana de configuración ahora puedes escribir las coordenadas tanto con coma como con punto y con espacios, corrigiéndose automáticamente para que la consulta nunca falle.
- Detección de redes Wi-Fi con inicio de sesión: si te conectas a una red pública (como en hoteles o cafeterías) que requiere iniciar sesión en el navegador, el complemento te avisa con claridad en lugar de dar un error extraño de datos.
- Protección contra pulsaciones repetidas: si pulsas varias veces seguidas el atajo del clima mientras está consultando en internet, el complemento ignora las pulsaciones repetidas para no saturar la conexión ni repetir la voz.
- Guardado seguro de tu ciudad y preferencias: tus opciones se graban de manera protegida para que nunca se pierda tu ciudad seleccionada si el ordenador se apaga de golpe.
- Cierre limpio de la ventana de opciones: al guardar o pulsar cancelar, las comprobaciones en segundo plano se detienen al instante, permitiendo que la ventana se cierre de inmediato sin trabar NVDA.
- Más tipos de clima traducidos: se añadieron descripciones en español e inglés para condiciones como llovizna helada, chubascos de nieve y granizo.
- Detección de conflictos de teclado adaptada a tu equipo: el comprobador de conflictos de teclas ahora reconoce correctamente si usas la distribución de teclado de sobremesa o de ordenador portátil.

### Créditos y Agradecimientos

- Idea original: Inspirado en el concepto pionero de Weather Plus creado por Adriano Barbieri y colaboradores. ClimaAccesible fue reescrito desde cero para funcionar con Open-Meteo sin claves API, con fechas naturales en español y base de ciudades local.
- Datos del clima: Provistos por Open-Meteo bajo licencia Creative Commons Atribución 4.0 (CC BY 4.0).
