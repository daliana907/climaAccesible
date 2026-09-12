# Nota técnica para revisores — Clima Accesible

*Versión 1.6 · Complemento para NVDA · Autora: Daliana*

Este documento describe qué toca el complemento en el sistema, qué permisos
pide y por qué. Está pensado para quien revisa el código antes de instalarlo o
publicarlo.

---

## Alcance

Clima Accesible anuncia por voz el tiempo actual y el pronóstico de los próximos
días para la ciudad que la usuaria elija. La usuaria decide además qué datos
quiere oír, de una lista de veintitantos, para que el anuncio no sea más largo
de lo necesario.

## Interfaces del sistema que utiliza

**Ninguna.**

El complemento no lee ni escribe en el registro de Windows, no carga ninguna
DLL, no ejecuta PowerShell ni ningún otro programa externo, y no usa `ctypes`.
Su único trato con el exterior es una petición HTTPS al servicio del tiempo.

## Permisos elevados

**Ninguno.** El complemento nunca pide permisos de administrador y nunca los
necesita. No hay ninguna llamada a `runas`, `ShellExecute` ni equivalente en
todo el código.

## Ubicación

El complemento **nunca le pregunta al sistema operativo dónde está el equipo**.
No usa el servicio de ubicación de Windows, ni geolocalización por dirección IP,
ni ningún otro método automático.

La ciudad se elige a mano, de tres listas encadenadas —país, región y ciudad—
que salen de `geodata.json`, un archivo incluido en el propio complemento. Ese
archivo es de solo lectura y hace que no haga falta ningún servicio de búsqueda
de lugares.

## Red

Un único servicio, y ninguno más:

**`https://api.open-meteo.com/v1/forecast`**

Open-Meteo es un servicio meteorológico abierto, gratuito para uso no comercial
y **que no requiere registro ni clave de API**. El complemento no tiene ninguna
credencial incrustada porque no hace falta ninguna.

Lo que se envía en cada petición:

- La latitud y la longitud de la ciudad que la usuaria eligió de la lista.
- Los nombres de los campos meteorológicos que tiene marcados en la
  configuración. Solo se piden los que se van a leer.
- La unidad de viento y la cantidad de días de pronóstico.

Lo que **no** se envía: ningún identificador de la usuaria ni del equipo,
ninguna cookie, ningún dato personal, ninguna dirección IP que el complemento
añada por su cuenta. No hay telemetría ni comprobación de actualizaciones.

Todas las peticiones tienen un límite de quince segundos. Los fallos de red
—sin internet, servidor caído, tiempo agotado— se anuncian con un mensaje que
explica qué pasó, en lugar de quedarse en silencio.

## Almacenamiento

Un solo archivo, `climaAccesible.json`, dentro de la carpeta de configuración
del usuario de NVDA (`globalVars.appArgs.configPath`). Contiene la ciudad, sus
coordenadas, la región, el país, qué datos se quieren oír y cuántos días de
pronóstico.

El complemento no escribe en ningún otro sitio.

## Hilos

Cada consulta al servicio del tiempo se ejecuta en su propio hilo `daemon`, para
que NVDA no se quede esperando la respuesta. Un evento `_stopping` los detiene
si NVDA se cierra o el complemento se descarga, y todas las funciones lo
comprueban antes de hablar, para no anunciar el resultado de una consulta que ya
no interesa.

## Pruebas automáticas

El complemento incluye 43 pruebas que se ejecutan en cada envío a GitHub. Usan
un NVDA simulado y no consultan el servicio real del tiempo.

---

# Technical note for reviewers — Accessible Weather

*Version 1.6 · NVDA add-on · Author: Daliana*

This document describes what the add-on touches on the system, what permissions
it requests and why. It is intended for anyone reviewing the code before
installing or publishing it.

## Scope

Accessible Weather announces the current weather and the forecast for the coming
days for the city the user picks. The user also chooses which data to hear, from
a list of some twenty-odd fields, so the announcement is no longer than needed.

## System interfaces used

**None.**

The add-on neither reads nor writes the Windows registry, loads no DLL, runs
neither PowerShell nor any other external program, and does not use `ctypes`.
Its only dealing with the outside world is an HTTPS request to the weather
service.

## Elevated privileges

**None.** The add-on never requests administrator privileges and never needs
them. There is no call to `runas`, `ShellExecute` or any equivalent anywhere in
the code.

## Location

The add-on **never asks the operating system where the machine is**. It uses
neither the Windows location service, nor IP-based geolocation, nor any other
automatic method.

The city is chosen by hand, from three chained lists — country, region and city
— that come from `geodata.json`, a file bundled with the add-on itself. That
file is read-only and removes the need for any place-lookup service.

## Network

A single service, and no other:

**`https://api.open-meteo.com/v1/forecast`**

Open-Meteo is an open weather service, free for non-commercial use, and **it
requires neither registration nor an API key**. The add-on embeds no credential
because none is needed.

What each request sends:

- The latitude and longitude of the city the user picked from the list.
- The names of the weather fields ticked in the settings. Only the ones that
  will be read are requested.
- The wind unit and the number of forecast days.

What is **not** sent: no user or machine identifier, no cookie, no personal
data, no IP address added by the add-on itself. There is no telemetry and no
update check.

Every request is bounded at fifteen seconds. Network failures — no internet,
server down, timeout — are announced with a message explaining what happened,
rather than falling silent.

## Storage

One file, `climaAccesible.json`, inside NVDA's user configuration folder
(`globalVars.appArgs.configPath`). It holds the city, its coordinates, the
region, the country, which data to announce and how many forecast days.

The add-on writes nowhere else.

## Threads

Each query to the weather service runs on its own `daemon` thread, so NVDA never
waits on the response. A `_stopping` event stops them if NVDA closes or the
add-on is unloaded, and every function checks it before speaking, so the result
of a query that no longer matters is never announced.

## Automated tests

The add-on ships with 43 tests that run on every push to GitHub. They use a
simulated NVDA and do not contact the real weather service.
