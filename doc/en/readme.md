# Accessible Weather for NVDA

- Author: Daliana
- Version: 1.8
- Compatibility: NVDA 2023.1 and later
- License: GNU GPL v2

[Leer en español](../es/readme.md)

---

## English Version

Accessible Weather is an NVDA add-on designed to announce current weather and future forecasts quickly, comfortably, and without complications.

### Key Highlights

- Works out of the box: Powered by Open-Meteo open weather API. No account sign-ups or private API keys needed. Install it, pick your city, and you are ready.
- Easy-to-understand forecast: Clearly speaks today, tomorrow, and subsequent days with natural dates without repeating days or mixing up timestamps.
- Rain periods by time of day: If rain is expected, it announces whether it will fall in the morning, afternoon, evening, or all day long.
- Offline city database: Includes an offline directory of over 50,000 localities organized by country, region/state, and city, eliminating the need for GPS or special permissions.
- Customizable weather details: Choose which parameters you want to hear via simple checkboxes, including feels-like temperature, humidity, wind, pressure, UV index, and sunrise/sunset times.

### Keyboard Shortcuts

- NVDA + W: Announce current weather conditions.
- NVDA + Shift + W: Announce upcoming forecast.
- NVDA + Control + W: Open configuration dialog to select your city or change options.

### Tools Menu

You can also access the add-on from NVDA Menu > Tools > Accessible Weather:

- Add-on settings: Open configuration dialog.
- Check shortcut conflicts with other add-ons...: Scan for overlapping shortcuts with other installed add-ons.

### Getting Started

1. Press NVDA + Control + W to open the settings dialog.
2. Select your country from the Country dropdown.
3. Tab to Region / State and choose yours.
4. Tab to City and choose your locality.
5. Check the weather items you want announced and click Save.

---

## What's new in 1.8.1 (13 September 2026)

- More reliable weather queries: strengthened and unified the way the add-on communicates with the weather data service, so both current weather and multi-day forecast queries handle connection errors more robustly and consistently.
- Internal cleanup and complete technical documentation of all add-on functions.

## What's new in 1.8 (13 September 2026)

- Smart remaining hours detection: when checking current weather or today's forecast, the add-on automatically filters out elapsed hours, preventing past rain periods (such as early morning or dawn rain) from being announced when querying in the afternoon or evening, and aligning today's weather condition with the remainder of the day so past drizzle is not carried over when only a residual probability remains.
- Accurate rain forecast across all time zones: when querying a city in a different time zone than your computer, the add-on now properly aligns that city's local hours, accurately announcing whether rain will fall in the morning, afternoon, or evening.
- Natural sunlight duration phrasing: daylight duration is announced naturally with proper singular and plural phrasing (such as "1 hour and 1 minute").
- Flexible coordinate inputs: you can now type coordinates in settings using either commas or dots and with extra spaces, and they will be normalized automatically so queries never fail.
- Captive portal detection on public Wi-Fi: if you connect to a public Wi-Fi network (such as hotels or airports) that requires a browser login, the add-on gives you a clear announcement instead of a raw data error.
- Protection against repeated key presses: pressing the weather shortcuts repeatedly while a request is already in progress will ignore extra presses to avoid clogging your connection or repeating speech.
- Safe settings saving: your city and preference settings are saved reliably so your configuration is never lost if the computer shuts down unexpectedly.
- Clean settings dialog dismissal: saving or canceling settings stops background timers immediately, allowing the window to close smoothly without freezing NVDA.
- Expanded translated weather codes: added clear descriptions in Spanish and English for freezing drizzle, snow showers, and hail.
- Layout-aware shortcut conflict auditing: the shortcut conflict checker now correctly matches gestures whether you are using a desktop or laptop keyboard layout.

### Credits

- Inspired by Weather Plus by Adriano Barbieri and contributors.
- Weather data provided by Open-Meteo under CC BY 4.0.
