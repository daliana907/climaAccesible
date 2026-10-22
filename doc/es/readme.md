# ClimaAccesible

* Autor: Daliana (Inspirado en Weather Plus de Adriano Barbieri)
* Versión: 1.9.10
* Compatibilidad con NVDA: 2023.1 en adelante
* Descarga de la versión estable: https://github.com/daliana907/climaAccesible

Este complemento es la forma más rápida y directa de conocer el estado del clima y el pronóstico extendido, interactuando directamente desde tu lector de pantalla de manera natural.

Una vez instalado, elige tu ciudad de la lista. El complemento solo se conecta al pulsar NVDA+W (o Mayús+W para el pronóstico); no consulta la red en segundo plano. No hace falta crear cuentas ni conseguir claves privadas; está listo para usarse desde el primer momento.

ClimaAccesible interpreta los datos meteorológicos de forma inteligente. En lugar de leerte una lista fría de números, te relata el clima en formato conversacional y omite información redundante de la siguiente manera:

*   Omite probabilidades de lluvia falsas o residuales: si la probabilidad es menor al 15% y no hay acumulación en milímetros, el sistema directamente te dirá "Sin lluvias." en lugar de hacerte perder tiempo leyendo probabilidades nulas.
*   Resume temperaturas calcadas: si la máxima y la mínima del día son casi iguales, en lugar de leerte dos veces el mismo número te lo resume diciendo "temperatura constante rondando los...".
*   Filtra la información del sol: solo te informa a qué hora sale y se pone el sol si el día va a estar despejado. Si el cielo va a estar completamente nublado o lloviendo, omite la salida del sol para no alargar el mensaje con datos que no vas a poder ver ni aprovechar.

Para ofrecer reportes de precipitaciones exactos, el complemento se nutre de los datos del radar satelital. Si consultas el clima y el servicio detecta que se aproxima un chaparrón a tu zona dentro de las próximas horas, NVDA te dará un aviso explícito diciéndote en cuántos minutos comenzará a llover o en qué momento parará según la proyección.

El diseño del reporte procesa la descarga de datos en paralelo para cargar mucho más rápido y calcula con precisión las fases de la luna.

## Cómo usarlo

El uso es muy sencillo, manejado por tres atajos de teclado clave:

*   Pulsando NVDA + W, escucharás el reporte del clima actual en tu ciudad, incluyendo la alerta de lluvia a corto plazo.
*   Pulsando NVDA + Shift + W, el complemento te leerá el pronóstico extendido de los próximos días (1 a 16, según lo configurado) de forma natural.
*   Y pulsando NVDA + Control + W, se abrirá la ventana de configuración.

> En algunas instalaciones de Windows, NVDA + Shift + W y NVDA + Control + W pueden estar asignados también a funciones de la Lupa de Windows. Si no responde el clima, cambia uno de esos gestos desde Preferencias de NVDA > Gestos de entrada.

Desde el menú NVDA > Herramientas > ClimaAccesible también puedes usar **Consultar alertas meteorológicas oficiales**. No tiene gesto asignado por defecto, pero puedes asignarle uno desde Gestos de entrada. Además, NVDA+W y NVDA+Shift+W añaden automáticamente las alertas vigentes al final del reporte; puedes apagar esa inclusión con la casilla **Incluir alertas oficiales en los reportes de clima y pronóstico**.

En la configuración puedes buscar tu ciudad eligiendo primero tu país, después tu región o departamento y finalmente tu localidad. También tienes diversas opciones para activar o desactivar información complementaria: puedes hacer que te lea u oculte la sensación térmica, la humedad, el índice UV, la visibilidad reducida, la nubosidad, el punto de rocío y las fases de la luna.

Además, si tu conexión a internet es inestable, en la sección "Red y reintentos" puedes configurar cuántas veces el complemento intentará volver a conectarse automáticamente al servidor meteorológico en caso de fallo, y cuántos segundos esperar entre cada intento.

## Privacidad, ciudades y recuperación

*   El complemento no detecta tu ubicación automáticamente ni pide permiso de ubicación a Windows. Tú eliges la ciudad manualmente.
*   La base de ciudades funciona sin conexión. Cuando dos localidades de una misma región tienen el mismo nombre, la lista muestra sus coordenadas para que puedas distinguirlas.
*   Algunas regiones no contienen ciudades en la base. El complemento lo anuncia y te devuelve al selector de región; no deja el foco en un control desactivado.
*   Las regiones muy grandes muestran hasta 2.000 ciudades y avisan cuando se aplica ese límite.
*   La ciudad guardada conserva país y coordenadas redondeadas a cuatro decimales. No guarda una dirección, calle ni ubicación precisa.
*   Si el archivo de configuración se daña o es demasiado grande, se conserva una copia con la marca `corrupto.bak` y NVDA te avisa una vez.
*   Las consultas tienen un límite total de espera, usan conexión segura y reutilizan datos recientes durante cinco minutos para evitar repeticiones innecesarias.

## Alertas meteorológicas oficiales

La consulta de alertas es manual: no interrumpe tu trabajo ni genera avisos automáticos. Cuando hay cobertura, informa nivel amarillo, naranja, rojo o aviso, el fenómeno, las zonas y el final de vigencia si la fuente lo publica.

Actualmente usa estas fuentes oficiales o públicas que redistribuyen avisos oficiales:

*   **Uruguay:** alertas de INUMET, mediante datosUruguay.
*   **Estados Unidos:** National Weather Service.

La estructura está preparada para añadir otros países. Si tu país todavía no tiene fuente integrada, el complemento lo dice claramente; nunca crea una alerta suponiéndola a partir del pronóstico.

## Novedades en la versión 1.9.10

*   Alertas oficiales: las zonas se anuncian solo con los departamentos, sin enumerar cada localidad, para un anuncio más corto.

## Novedades en la versión 1.9.9

*   Alertas oficiales: el fenómeno se lee con nombre natural ("Tormentas eléctricas" en vez de "tormentas_electricas").
*   Las zonas se agrupan por departamento y se leen como texto, sin listas técnicas ni datos cortados.
*   Se muestra la vigencia con fecha y hora cuando la fuente la publica (por ejemplo, INUMET).

## Novedades en la versión 1.9.8

*   Consulta de alertas que no se bloquea: si quedaba marcada en curso, se libera sola.
*   Aviso de espera que indica que puede tardar unos segundos.

## Novedades en la versión 1.9.7

*   NVDA+W y NVDA+Shift+W añaden las alertas oficiales vigentes al final del reporte, consultadas en paralelo para no demorar el anuncio. Si fallan o no hay, el reporte sigue igual.
*   Nueva casilla en configuración para incluir o no las alertas en los reportes.

## Novedades en la versión 1.9.6

*   Nueva consulta manual de alertas meteorológicas oficiales desde el menú Herramientas.
*   Niveles y avisos de fuentes diferentes unificados en un formato accesible.
*   Sin alertas inventadas: los países sin proveedor integrado reciben un mensaje claro de falta de cobertura.

## Créditos de terceros

*   Datos meteorológicos: Open-Meteo (https://open-meteo.com), uso gratuito sin clave.
*   Base geográfica local: datos de localidades (país/región/ciudad). Atribución GeoNames/CC-BY pendiente de completar en la documentación.

## Créditos

La idea original estuvo inspirada en el gran complemento Weather Plus creado por Adriano Barbieri. Esta versión fue creada desde cero con tecnología moderna para evitar el uso de claves de API y lograr descripciones mucho más orgánicas. Todos los datos meteorológicos provienen de la plataforma de acceso público y gratuito Open-Meteo (https://open-meteo.com).

## Licencia y derechos de autor

Este complemento está protegido por derechos de autor y se distribuye bajo los términos de la Licencia Pública General de GNU (GPL), versión 2 o posterior. Eres libre de usar, modificar y distribuir este software bajo dichas condiciones. Puedes consultar el texto completo de la licencia en: https://www.gnu.org/licenses/gpl-2.0.html

Aclaración sobre el uso de Inteligencia Artificial: Para programar partes de la lógica interna de este complemento y para redactar estos manuales me apoyé en herramientas de Inteligencia Artificial, tal como sugieren declarar las reglas de publicación de NVDA. De todos modos, cada línea de código y cada función fueron dirigidas, revisadas y probadas a fondo por mí.
