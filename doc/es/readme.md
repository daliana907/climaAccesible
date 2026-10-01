# ClimaAccesible

* Autor: Daliana (Inspirado en Weather Plus de Adriano Barbieri)
* Compatibilidad con NVDA: 2023.1 en adelante
* Descarga de la versión estable: https://github.com/daliana907/climaAccesible

Este complemento es la forma más rápida y directa de conocer el estado del clima y el pronóstico extendido, interactuando directamente desde tu lector de pantalla de manera natural.

Una vez instalado, al elegir tu ciudad de la lista, el sistema se conecta de inmediato al servicio meteorológico. No hace falta crear cuentas ni conseguir claves privadas; está listo para usarse desde el primer momento.

ClimaAccesible interpreta los datos meteorológicos de forma inteligente. En lugar de leerte una lista fría de números, te relata el clima en formato conversacional y omite información redundante de la siguiente manera:

*   Omite probabilidades de lluvia falsas o residuales: si la probabilidad es menor al 15% y no hay acumulación en milímetros, el sistema directamente te dirá "Sin lluvias." en lugar de hacerte perder tiempo leyendo probabilidades nulas.
*   Resume temperaturas calcadas: si la máxima y la mínima del día son casi iguales, en lugar de leerte dos veces el mismo número te lo resume diciendo "temperatura constante rondando los...".
*   Filtra la información del sol: solo te informa a qué hora sale y se pone el sol si el día va a estar despejado. Si el cielo va a estar completamente nublado o lloviendo, omite la salida del sol para no alargar el mensaje con datos que no vas a poder ver ni aprovechar.

Para ofrecer reportes de precipitaciones exactos, el complemento se nutre de los datos del radar satelital. Si consultas el clima y el servicio detecta que se aproxima un chaparrón a tu zona dentro de las próximas horas, NVDA te dará un aviso explícito diciéndote en cuántos minutos comenzará a llover o en qué momento parará según la proyección.

El diseño del reporte procesa la descarga de datos en paralelo para cargar mucho más rápido y calcula con precisión las fases de la luna.

## Cómo usarlo

El uso es muy sencillo, manejado por tres atajos de teclado clave:

*   Pulsando NVDA + W, escucharás el reporte del clima actual en tu ciudad, incluyendo la alerta de lluvia a corto plazo.
*   Pulsando NVDA + Shift + W, el complemento te leerá el pronóstico extendido de los próximos días de forma natural.
*   Y pulsando NVDA + Control + W, se abrirá la ventana de configuración.

En la configuración puedes buscar tu ciudad eligiendo primero tu país, después tu región o departamento y finalmente tu localidad. También tienes diversas opciones para activar o desactivar información complementaria: puedes hacer que te lea u oculte la sensación térmica, la humedad, el índice UV, la visibilidad reducida, la nubosidad, el punto de rocío y las fases de la luna.

Además, si tu conexión a internet es inestable, en la sección "Red y reintentos" puedes configurar cuántas veces el complemento intentará volver a conectarse automáticamente al servidor meteorológico en caso de fallo, y cuántos segundos esperar entre cada intento.

## Créditos

La idea original estuvo inspirada en el gran complemento Weather Plus creado por Adriano Barbieri. Esta versión fue creada desde cero con tecnología moderna para evitar el uso de claves de API y lograr descripciones mucho más orgánicas. Todos los datos meteorológicos provienen de la plataforma de acceso público y gratuito Open-Meteo (https://open-meteo.com).

## Licencia y derechos de autor

Este complemento está protegido por derechos de autor y se distribuye bajo los términos de la Licencia Pública General de GNU (GPL), versión 2 o posterior. Eres libre de usar, modificar y distribuir este software bajo dichas condiciones. Puedes consultar el texto completo de la licencia en: https://www.gnu.org/licenses/gpl-2.0.html

Aclaración sobre el uso de Inteligencia Artificial: Para programar partes de la lógica interna de este complemento y para redactar estos manuales me apoyé en herramientas de Inteligencia Artificial, tal como sugieren declarar las reglas de publicación de NVDA. De todos modos, cada línea de código y cada función fueron dirigidas, revisadas y probadas a fondo por mí.
