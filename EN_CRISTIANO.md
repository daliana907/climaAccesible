# Clima Accesible, explicado en cristiano

Esto es para cualquiera que quiera saber qué hace este complemento antes de
instalarlo, sin necesidad de saber programar.

## ¿Para qué sirve?

Dice en voz alta qué tiempo hace ahora mismo en tu ciudad y qué tiempo se espera
los próximos días. Tú eliges qué datos quieres oír —temperatura, viento, lluvia,
hora del amanecer, índice ultravioleta y unos cuantos más— para que el anuncio no
sea más largo de lo que necesitas.

## ¿Cómo sabe dónde estoy?

**Porque se lo dices tú.** No lo averigua solo.

El complemento no le pregunta a Windows dónde estás, no mira tu dirección de
internet para deducirlo, no usa ningún servicio de localización. Eliges tu
ciudad a mano, de tres listas: primero el país, después la región y después la
ciudad. Esas listas vienen dentro del propio complemento, así que ni siquiera
hace falta internet para elegirla.

Si te mudas o quieres el tiempo de otro sitio, cambias la ciudad y ya.

## ¿Pide permisos de administrador?

No. Nunca. Ni los pide ni los necesita para nada.

## ¿Toca algo de mi sistema?

No. Es el más sencillo de los tres en este sentido: no toca el registro de
Windows, no ejecuta ningún programa, no carga ninguna biblioteca del sistema.
Lo único que hace con el exterior es pedirle el tiempo a un servidor.

## ¿Qué manda a internet?

Solo esto: las coordenadas de la ciudad que elegiste, y los nombres de los datos
que tienes marcados. Nada más.

No manda tu nombre, ni el de tu equipo, ni nada que te identifique. No hay
cookies. No hay cuenta ni contraseña, porque el servicio que usa —Open-Meteo—
es abierto y gratuito y no pide registrarse. Por eso el complemento tampoco
lleva ninguna clave escondida dentro: no le hace falta.

Tampoco busca actualizaciones ni manda estadísticas de uso.

## ¿Y si no tengo internet?

Te lo dice. Cada tipo de fallo tiene su propio mensaje: que no hay conexión, que
el servidor no respondió, que tardó demasiado. No se queda callado dejándote sin
saber qué pasó.

Todas las consultas tienen quince segundos de límite, así que nunca se queda
esperando indefinidamente.

## ¿Guarda algo en mi equipo?

Un solo archivo, dentro de la carpeta de configuración de NVDA, con tu ciudad,
sus coordenadas y qué datos quieres oír. Nada más.

## ¿Va a poner lento mi equipo?

No. Cada consulta al servidor se hace en segundo plano, así que NVDA sigue
respondiendo mientras espera. Y si cierras NVDA en mitad de una consulta, esa
consulta se cancela sola en vez de anunciar un resultado que ya no querías.

## ¿Puedo fiarme de que hace lo que dice?

El código está publicado entero y cualquiera puede leerlo. Tiene 43 pruebas
automáticas que se ejecutan solas cada vez que se sube un cambio, y que no
tocan el servicio real del tiempo.

Y escribe en el registro de NVDA lo que va haciendo, así que si algo falla ahí
queda la explicación.
