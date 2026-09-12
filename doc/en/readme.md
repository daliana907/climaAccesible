# Accessible Weather for NVDA

Author: Daliana
Version: 1.7
Compatibility: NVDA 2023.1 or later
License: GNU GPL v2

Accessible Weather is an NVDA add-on providing fast, accurate current weather and forecasts without needing API keys or account registration.

### Key Highlights
- Works out of the box: Powered by Open-Meteo open weather API. No signup or private API keys required.
- Natural multi-day forecasts: Plain-language summaries for today, tomorrow, and upcoming days with temperature trends and precipitation periods.
- Offline city database: Over 50,000 cities organized by Country, Province/State, and City.
- Customizable speech output: Toggle feels-like temperature, humidity, wind, pressure, UV index, and sunrise/sunset times.

### Keyboard Shortcuts
- NVDA + W: Announce current weather conditions.
- NVDA + Shift + W: Announce forecast for upcoming days.
- NVDA + Control + W: Open settings dialog.

### NVDA Tools Menu
You can also access the add-on from NVDA > Tools > ClimaAccesible:
- Add-on settings: Open configuration dialog.
- Check add-on conflicts: Check if any other installed add-on conflicts with weather shortcuts.
- Documentation: Open this user guide.

### Getting Started
1. Press NVDA + Control + W to open settings.
2. Choose your Country, Province/State, and City.
3. Select your desired weather details and click Save.

## What's new in 1.6 (12 September 2026)

### Improved

- Clean teardown of Tools menu items on addon termination or reload, preventing orphaned UI handles.
- The documentation menu item automatically detects NVDA's active language and opens the Spanish or English guide accordingly.
- The settings dialog now implements standard affirmative and escape IDs (`wx.ID_OK`, `wx.ID_CANCEL`) along with button mnemonics for seamless Enter/Escape keyboard navigation.

---

## What's new in 1.5 (8 September 2026)

### Fixed

- Settings could not be saved: the code used a value that did not exist and the operation failed.
- The multi-day forecast was always read in Spanish, even with NVDA in another language. It is now translated like everything else.
- About 45 weather vocabulary phrases (wind directions, sky conditions, times of day) were not translatable. They now are, and were translated into English.
- Several technical names from the weather service were wrongly exposed as translatable text.

### Internal changes

- The current weather and forecast queries were split into named pieces: build the request, read the answer, write each sentence.
- The part that decides how each day's rain is described is now separate and has its own tests.
- Added texts were reworded into the neutral Spanish used across the add-on.
- Added 43 automatic checks that run on their own on GitHub with every change.

The full history of every version is in the CHANGELOG.md file of the
add-on repository.

### Credits
- Inspired by Weather Plus by Adriano Barbieri and contributors.
- Weather data provided by Open-Meteo under CC BY 4.0.
