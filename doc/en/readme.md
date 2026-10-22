# Accessible Weather for NVDA

- Author: Daliana
- Version: 1.9.9
- Compatibility: NVDA 2023.1 and later
- License: GNU GPL v2

[Leer en español](../es/readme.md)

---

## English Version

Accessible Weather is an NVDA add-on designed to announce current weather and future forecasts quickly, comfortably, and without complications.

### Key Highlights

- Works out of the box: Powered by Open-Meteo open weather API. No account sign-ups or private API keys needed. Install it, pick your city, and you are ready. The add-on only connects to the network when you press NVDA+W (or Shift+W); it never polls in the background.
- Easy-to-understand forecast: Clearly speaks today, tomorrow, and subsequent days with natural dates without repeating days or mixing up timestamps.
- Rain periods by time of day: If rain is expected, it announces whether it will fall in the morning, afternoon, evening, or all day long.
- Offline city database: Includes an offline directory of over 50,000 localities organized by country, region/state, and city, eliminating the need for GPS or special permissions.
- Customizable weather details: Choose which parameters you want to hear via simple checkboxes, including feels-like temperature, humidity, wind, pressure, UV index, and sunrise/sunset times.

### Keyboard Shortcuts

- NVDA + W: Announce current weather conditions.
- NVDA + Shift + W: Announce upcoming forecast (1 to 16 days, as configured in settings).
- NVDA + Control + W: Open configuration dialog to select your city or change options.

> On some Windows installations, NVDA + Shift + W and NVDA + Control + W can also be assigned to Windows Magnifier commands. If Weather does not respond, change one of the conflicting gestures in NVDA Preferences > Input Gestures.

From NVDA Menu > Tools > Accessible Weather, you can also use **Check official weather alerts**. It has no default gesture, but you can assign one in Input Gestures. NVDA+W and NVDA+Shift+W also append current official alerts to the end of the report; you can turn this off with the **Include official alerts in weather and forecast reports** checkbox.

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

### Privacy, Cities and Recovery

- The add-on does not detect your location automatically and does not request Windows location permission. You choose the city yourself.
- The city database works offline. When two cities in the same region have the same name, the list shows their coordinates so you can tell them apart.
- Some regions have no cities in the database. The add-on announces this and returns focus to the region selector.
- Very large regions show up to 2,000 cities and announce when that limit is applied.
- Saved locations contain country and coordinates rounded to four decimal places. No street address or precise location is stored.
- If the settings file is damaged or too large, a `corrupto.bak` copy is retained and NVDA announces the problem once.
- Requests have a total time limit, use a secure connection, and reuse recent data for five minutes to avoid unnecessary repeated requests.

### Official Weather Alerts

Alert checking is manual: it does not interrupt your work or create automatic notifications. Where coverage is available, it reports yellow, orange, red, or advisory level, the event, affected areas, and end time when the source provides them.

Current official or official-data sources are:

- **Uruguay:** INUMET alerts, through datosUruguay.
- **United States:** National Weather Service.

The provider structure is ready for additional countries. If a country does not yet have an integrated official source, the add-on says so clearly; it never creates an alert by guessing from the forecast.

---

## What's new in 1.9.9

- Official alerts: the phenomenon is spoken with a natural name ("Tormentas eléctricas" instead of "tormentas_electricas").
- Areas are grouped by department and read as text, without technical lists or cut-off data.
- Validity date and time are shown when the source publishes them (for example, INUMET).

## What's new in 1.9.8

- Non-blocking alert queries: a stuck in-progress mark releases itself.
- Waiting message notes the query may take a few seconds.

## What's new in 1.9.7

- NVDA+W and NVDA+Shift+W append current official alerts to the end of the report, fetched in parallel so the announcement is not delayed. If alerts fail or there are none, the report is unchanged.
- New settings checkbox to include official alerts in reports or not.

## What's new in 1.9.6

- New manual official-weather-alert query in the Tools menu.
- Accessible normalized presentation of warning levels from different official sources.
- Honest coverage: countries without an integrated provider receive a clear availability message instead of forecast-based guessed alerts.

## What's new in 1.9.5

- Zero-coordinate fix: cities on the equator (latitude 0.0) or the Greenwich meridian (longitude 0.0) are no longer misdetected as unconfigured.
- Localized settings: all 29 weather option checkboxes are now shown correctly translated in the supported languages.
- 15-minute rain radar sync: rain-radar calculation aligned to the queried city's time zone, avoiding offsets with the local computer clock.
- Smart nighttime UV filter: UV index is automatically omitted when it is 0.0 at night for a cleaner report.
- Instant loading: background preload of the geographic database so the settings dialog opens instantly.
- Threading robustness: clean, responsive shutdown of background requests and tasks without slowing NVDA close or restart.

## What's new in 1.9.4

- Maintenance and stability improvements (no behavior changes).

## What's new in 1.9.3

- Maintenance and stability improvements (no behavior changes).

## What's new in 1.9.2

- Maintenance and stability improvements (no behavior changes).

## What's new in 1.9.1

- Fast 'No rain' announcements: If precipitation probability is under 15% with zero accumulation, the add-on immediately announces 'No rain' instead of reading zero percentages.
- Configurable network retries: New options in settings allow you to define maximum connection retries and wait time to handle unstable networks.
- Bulletproof error handling: The add-on safely catches networking thread crashes to prevent silent hangups.

## What's new in 1.9.0

- Smarter daily add-on redesign: 15-minute satellite rain radar with real-time alerts telling in how many minutes rain will start or stop.
- Extended forecast now detects intermittent storms and announces the exact hour rain will begin.
- Smart report filter: omits UV index at night, hides wind when calm, and summarizes identical high/low temperatures in a single sentence.
- Optional moon-phase announcements.
- Faster parallel downloads: current weather loads about twice as fast. Removed little-used features such as total daylight-hours count.

## What's new in 1.8.2 (18 September 2026)

- Accurate snow descriptions: corrected a condition description that reported "fine hail" when conditions actually called for snow grains, preserving hail announcements strictly for actual storms.
- Resilient daily forecast: if hourly data from the weather service contains an unexpected timestamp format, the add-on skips that specific entry and presents the rest of the daily forecast without interruption.
- Quicker server error reporting: when the weather API reports an internal server error, the add-on notifies you immediately without waiting through ineffective retry cycles.

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

### Third-party credits

*   Weather data: Open-Meteo (https://open-meteo.com), free use without API key.
*   Local geographic database: locality data (country/region/city). GeoNames/CC-BY attribution pending in documentation.

### Credits

- Inspired by Weather Plus by Adriano Barbieri and contributors.
- Weather data provided by Open-Meteo under CC BY 4.0.
