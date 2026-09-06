# Accessible Weather (ClimaAccesible) for NVDA

* **Author:** Daliana
* **Version:** 1.4
* **Compatibility:** NVDA 2019.3 or later
* **License:** GNU General Public License v2.0 (GPLv2)

Accessible Weather (ClimaAccesible) is an accessible weather and multi-day forecast add-on for the NVDA screen reader. It allows users to check current weather conditions and detailed extended forecasts using simple, accessible keyboard shortcuts without requiring private API keys or accounts.

## Keyboard Shortcuts

* **NVDA + W**: Announces current weather conditions for the configured city.
* **NVDA + Shift + W**: Announces the multi-day extended weather forecast (1 to 14 days).
* **NVDA + Control + W**: Opens the accessible configuration dialog.
* **NVDA + N -> Tools -> ClimaAccesible**: Add-on menu (Settings, Check conflicts with other add-ons, Documentation).

## Getting Started

1. Press `NVDA + Control + W` to open the configuration dialog.
2. In the **Country** combo box, select your country (regions and cities load automatically).
3. Tab to **Region / Department** and choose yours.
4. Tab to **City** and select your city.
5. Check or uncheck the weather metrics you wish to hear.
6. Under **Extended Forecast**, choose the number of days to forecast (1 to 14).
7. Click **Save**.

> **Note:** Over 50,000 cities are stored locally in the add-on. No Internet connection is needed to browse or configure your location, only when requesting real-time weather updates.

## Current Weather (NVDA + W)

Announces real-time conditions. You can toggle which metrics you want to hear:
* Current temperature
* Sky condition
* Relative humidity
* Atmospheric pressure
* Wind speed and direction
* Wind gusts
* Sunrise and sunset times

## Extended Forecast (NVDA + Shift + W)

Announces daily forecasts in natural spoken language:
* Daily maximum and minimum temperatures
* Primary sky condition
* Maximum UV index
* Expected precipitation (rain/snow) and time-of-day breakdown (morning, afternoon, evening)
* Sunrise and sunset times

## Third-Party Data & Privacy

* Meteorological data is provided by [Open-Meteo](https://open-meteo.com/) under the [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) license.
* Geographical city database from [Countries States Cities Database](https://github.com/dr5hn/countries-states-cities-database) under the [Open Database License (ODbL 1.0)](https://opendatacommons.org/licenses/odbl/1-0/).
* Privacy: The add-on only sends latitude and longitude to Open-Meteo to fetch public forecast data. No personal data, tracking cookies, or user identifiers are collected or stored.

## Credits & Acknowledgements

* **Original concept & inspiration:** Inspired by the pioneering concept of **Weather Plus** by Adriano Barbieri and contributors. ClimaAccesible is an independent, ground-up rewrite designed to eliminate the need for private API keys, resolve non-English forecast date ambiguities, eliminate legacy binary dependencies, and provide an offline geographic database.
* **Meteorological Data:** Open-Meteo (CC BY 4.0).
* **Geographic Database:** Countries States Cities Database (ODbL 1.0).
* **Author & Maintainer:** Daliana.
* **License:** GNU General Public License v2.0 (GPLv2).

## Changelog

### Version 1.4
* Formal recognition and attribution added to Weather Plus (Adriano Barbieri and contributors) as conceptual inspiration.
* Complete internationalization: integrated 10 community translations (German, English, French, Italian, Japanese, Polish, Brazilian Portuguese, Russian, Turkish, Simplified Chinese) with compiled `.mo` catalogs.
* Bilingual documentation: English documentation in `doc/en/` and root `README.md`.
* Standardized GPLv2 license headers across all source code modules.

### Version 1.3
* Conflict auditor under Tools menu to diagnose shortcut collisions with other add-ons.
* Detailed network logging in `nvda.log` with HTTP response times and full exception traces.
* Fixed network import for response time calculations.

### Version 1.2
* AI usage declaration and third-party data documentation.
* Tested compatibility with NVDA 2026.2.

### Version 1.1
* Natural rain detection by time of day.
* Cascading offline city selection.
* Clean thread shutdown on NVDA restart.
