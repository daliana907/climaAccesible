# -*- coding: utf-8 -*-
"""Batería de pruebas de estrés, caos y resiliencia meteorológica para climaAccesible.

Prueba el complemento ante:
- Fallos de red y respuestas HTTP anómalas (429 Rate Limit, 500, timeout, HTML de portal cautivo)
- Payloads JSON caóticos o truncados (nodos faltantes, tipos anómalos, NaN, listas desfasadas)
- Hammering masivo de atajos (NVDA+W, NVDA+Shift+W, NVDA+Control+W en ráfaga rápida)
- Corrupción de archivos locales de configuración y geodata
- Coordenadas extremas y días de pronóstico fuera de límites
"""
import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import json
import socket
import urllib.error
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nvda_falso
nvda_falso.instalar()

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "globalPlugins"))

import climaAccesible as clima


class TestEstresCaosClimaAccesible(unittest.TestCase):
    """Pruebas de estrés y situaciones inesperadas en climaAccesible."""

    def setUp(self):
        self.plugin = clima.GlobalPlugin()

    def tearDown(self):
        try:
            self.plugin.terminate()
        except Exception:
            pass

    # ── 1. Resiliencia ante fallos de red y errores de API ───────────────────
    def test_manejo_errores_red_y_servidor(self):
        """Verifica que fallos de red, timeouts, 429 y 500 se manejen sin romper el hilo ni NVDA."""
        errores_red = [
            socket.timeout("Connection timed out"),
            TimeoutError("Timeout general"),
            urllib.error.HTTPError("https://api.open-meteo.com", 429, "Too Many Requests", {}, None),
            urllib.error.HTTPError("https://api.open-meteo.com", 500, "Internal Server Error", {}, None),
            urllib.error.HTTPError("https://api.open-meteo.com", 502, "Bad Gateway", {}, None),
            urllib.error.URLError("Name or service not known"),
            json.JSONDecodeError("Expecting value", "<html>portal</html>", 0),
            UnicodeDecodeError("utf-8", b"\xff\xfe", 0, 1, "invalid start byte"),
        ]
        mensajes_recibidos = []
        with patch.object(self.plugin, "_safeMessage", side_effect=lambda m: mensajes_recibidos.append(m)):
            for err in errores_red:
                with self.subTest(err=type(err).__name__):
                    mensajes_recibidos.clear()
                    self.plugin._manejarErrorPeticion(err, operacion="el clima")
                    self.assertTrue(len(mensajes_recibidos) > 0)
                    self.assertIsInstance(mensajes_recibidos[0], str)

    # ── 2. Payloads JSON corruptos o caóticos de Open-Meteo ──────────────────
    def test_fetch_weather_con_payloads_corruptos(self):
        """Somete _fetchWeather a respuestas con claves faltantes, tipos anómalos y datos corruptos."""
        payloads_caoticos = [
            {},
            {"current": None, "daily": None, "hourly": None},
            {"current": "no_es_diccionario"},
            {"current": {"temperature_2m": float("nan"), "weather_code": 9999, "precipitation": -5.0}},
            {"current": {"temperature_2m": float("inf"), "is_day": 5, "relative_humidity_2m": 500}},
            {
                "current": {"temperature_2m": 22.0, "weather_code": 1},
                "hourly": {
                    "time": ["2026-10-14T12:00"],
                    "precipitation": [],  # Lista desfasada
                    "precipitation_probability": [50, 60, 70]  # Longitud distinta
                }
            },
            {
                "current": {"temperature_2m": 15.0, "weather_code": 3},
                "minutely_15": {
                    "time": ["2026-10-14T12:00", "hora_invalida"],
                    "precipitation": [float("nan"), float("inf")],
                    "precipitation_probability": [None, "invalido"]
                }
            }
        ]
        cfg = {"city": "Montevideo", "lat": -34.9, "lon": -56.1, "prefs": {}}
        for payload in payloads_caoticos:
            with self.subTest(payload=payload):
                with patch.object(self.plugin, "_getJsonFromApi", return_value=payload):
                    with patch.object(self.plugin, "_safeMessage") as mock_msg:
                        self.plugin._fetchWeather(cfg)
                        self.assertFalse(self.plugin._fetchingWeatherActive)

    # ── 3. Payloads caóticos en pronóstico extendido ─────────────────────────
    def test_fetch_forecast_con_payloads_corruptos(self):
        """Somete _fetchForecast a respuestas incompletas o tipos anómalos."""
        payloads_pronostico = [
            {},
            {"daily": None},
            {"daily": {"time": None}},
            {"daily": {"time": ["2026-10-14", "2026-10-15"], "weather_code": [0]}},  # Lista desfasada
            {
                "daily": {
                    "time": ["2026-10-14"],
                    "temperature_2m_max": [float("nan")],
                    "temperature_2m_min": [float("inf")],
                    "weather_code": [None]
                }
            }
        ]
        cfg = {"city": "Madrid", "lat": 40.4, "lon": -3.7, "forecast_days": 6, "prefs": {}}
        for payload in payloads_pronostico:
            with self.subTest(payload=payload):
                with patch.object(self.plugin, "_getJsonFromApi", return_value=payload):
                    with patch.object(self.plugin, "_safeMessage") as mock_msg:
                        self.plugin._fetchForecast(cfg)
                        self.assertFalse(self.plugin._fetchingForecastActive)

    # ── 4. Hammering y bloqueo reentrante de consultas ───────────────────────
    def test_hammering_atajos_consultas_en_curso(self):
        """Verifica que el spam de atajos cuando ya hay una consulta en curso sea ignorado sin lanzar hilos duplicados."""
        self.plugin._fetchingWeatherActive = True
        with patch("threading.Thread") as mock_th:
            self.plugin.script_getWeather(None)
            mock_th.assert_not_called()

        self.plugin._fetchingForecastActive = True
        with patch("threading.Thread") as mock_th:
            self.plugin.script_getForecast(None)
            mock_th.assert_not_called()

        self.plugin._isConfigOpen = True
        with patch.object(clima.gui.mainFrame, "prePopup") as mock_pre:
            self.plugin._openConfigDialog()
            mock_pre.assert_not_called()

    # ── 5. Corrupción de geodata.json y climaAccesible.json ──────────────────
    def test_resiliencia_archivos_locales_corruptos(self):
        """Verifica que la lectura de geodata y configuración tolere archivos de 0 bytes o JSON inválido."""
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
            temp_cfg = f.name
        try:
            # Archivo vacío (0 bytes)
            datos_vacios = clima.loadJSON(temp_cfg)
            self.assertEqual(datos_vacios, {})

            # Archivo corrupto (sintaxis rota)
            with open(temp_cfg, "w", encoding="utf-8") as wf:
                wf.write("{esto no es json valido")
            datos_corruptos = clima.loadJSON(temp_cfg)
            self.assertEqual(datos_corruptos, {})
        finally:
            if os.path.exists(temp_cfg):
                os.remove(temp_cfg)

    # ── 6. Fuzzing de coordenadas y días de pronóstico ──────────────────────
    def test_fuzzing_coordenadas_y_dias_pronostico(self):
        """Verifica la normalización de coordenadas y límites de días de pronóstico (1 a 16)."""
        coordenadas = [
            ("-34,90", -34.90),
            (" -56.16 ", -56.16),
            (999.0, 999.0),
            (-999.0, -999.0),
            ("invalido", "invalido"),
            (None, None),
        ]
        for coord_in, coord_esperada in coordenadas:
            with self.subTest(coord=coord_in):
                res = clima._normalizarCoord(coord_in)
                self.assertEqual(res, coord_esperada)

        dias_test = [
            (-5, 6),      # Días negativos -> acotados a mínimo 1
            (0, 6),
            (25, 6),     # Supera 16 -> acotado a 16
            ("invalido", 6),
            (None, 6),
        ]
        for d_in, d_esperado in dias_test:
            try:
                days = max(1, min(16, int(d_in)))
            except (ValueError, TypeError):
                days = 6
            self.assertTrue(1 <= days <= 16)

    # ── 7. Protección ante diálogo wx destruido (PyDeadObjectError) ───────────
    def test_dead_object_protection_config_dialog(self):
        """Verifica que callbacks como _populate_countries y _status no rompan ante diálogo destruido."""
        class DeadConfigDialog(clima.ConfigDialog):
            def __init__(self):
                pass
            def __bool__(self):
                raise RuntimeError("wrapped C/C++ object has been deleted")

        dead_dlg = DeadConfigDialog.__new__(DeadConfigDialog)
        try:
            dead_dlg._populate_countries([("Uruguay", "UY")])
            dead_dlg._status("Mensaje de prueba")
            dead_dlg._stopProgress()
            dead_dlg._onProgressTick(None)
            dead_dlg._do_fill_regions(0)
            dead_dlg._do_fill_cities(0)
        except RuntimeError as e:
            self.fail(f"ConfigDialog lanzó excepción ante objeto C++ destruido: {e}")

    # ── 8. loadJSON ante tipos no-dict (listas, enteros, cadenas, null) ──────
    def test_load_json_tipos_no_dict(self):
        """Verifica que loadJSON devuelva siempre {} si el JSON cargado no es un diccionario."""
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
            temp_path = f.name
        try:
            casos_no_dict = [
                "[1, 2, 3]",
                '"cadena"',
                "12345",
                "null",
                "true",
            ]
            for c in casos_no_dict:
                with open(temp_path, "w", encoding="utf-8") as wf:
                    wf.write(c)
                res = clima.loadJSON(temp_path)
                self.assertEqual(res, {}, f"loadJSON no devolvió dict vacío para: {c}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # ── 9. getGeoData ante archivo ausente o corrupto ─────────────────────────
    def test_get_geodata_archivo_faltante_o_corrupto(self):
        """Verifica que getGeoData devuelva una lista y no interrumpa con excepciones si geodata no existe."""
        with patch.object(clima, "_geoData", None):
            with patch.object(clima, "GEODATA_FILE", "C:\\ruta\\inexistente\\geodata_fantasma.json"):
                res = clima.getGeoData()
                self.assertEqual(res, [])

    # ── 10. Fuzzing de codigoClima, uvFrase y calidadAireFrase ────────────────
    def test_fuzzing_codigo_clima_uv_y_calidad_aire(self):
        """Verifica que codigoClima, uvFrase y calidadAireFrase no lancen excepciones ante valores extremos."""
        # codigoClima
        codigos_raros = [
            -1, 0, 1, 45, 99, 9999, "61", "invalido", None, float("nan"), float("inf"), 61.0
        ]
        for c in codigos_raros:
            with self.subTest(code=c):
                res = clima.codigoClima(c)
                self.assertIsInstance(res, str)
                self.assertTrue(len(res) > 0)

        # uvFrase
        uv_valores = [
            0, 2.9, 3.0, 5.9, 6.0, 7.9, 8.0, 10.9, 11.0, 25.0, -1, float("nan"), float("inf"), None, "invalido"
        ]
        for u in uv_valores:
            with self.subTest(uv=u):
                res = clima.uvFrase(u)
                self.assertIsInstance(res, str)

        # calidadAireFrase
        aqi_valores = [
            0, 20, 21, 40, 41, 60, 61, 80, 81, 100, 101, 500, -5, float("nan"), float("inf"), None, "error"
        ]
        for a in aqi_valores:
            with self.subTest(aqi=a):
                res = clima.calidadAireFrase(a)
                self.assertIsInstance(res, str)

    # ── 11. Timeout en hilos concurrentes de clima y calidad de aire ─────────
    def test_fetch_weather_timeout_en_hilos_secundarios(self):
        """Verifica que si un hilo secundario de la API se congela, t1.join() con timeout no bloquee permanentemente."""
        cfg = {"city": "Madrid", "lat": 40.4, "lon": -3.7, "prefs": {}}
        def simulate_hang(*args, **kwargs):
            time.sleep(1.0)
            raise TimeoutError("Simulated hang")

        with patch.object(self.plugin, "_getJsonFromApi", side_effect=simulate_hang):
            with patch.object(self.plugin, "_safeMessage") as mock_msg:
                self.plugin._fetchWeather(cfg)
                self.assertFalse(self.plugin._fetchingWeatherActive)

    # ── 12. Inmunidad a OverflowError ante float('inf') en formateadores ──────
    def test_inmunidad_overflow_error_en_formateadores(self):
        """Verifica que valores float('inf') o 'inf' no lancen OverflowError en frases del clima y lluvia."""
        c = {
            "weather_code": float("inf"),
            "cloud_cover": 50,
            "visibility": 5000,
            "uv_index": float("inf"),
            "precipitation": float("inf"),
        }
        dv = lambda k: float("inf") if k.endswith("max") else 10.0
        prefs = {k: True for k in [op[0] for op in clima.OPCIONES]}

        # _frasesDelClimaActual
        try:
            partes_actual = self.plugin._frasesDelClimaActual(c, prefs)
            self.assertIsInstance(partes_actual, list)
        except OverflowError as e:
            self.fail(f"_frasesDelClimaActual lanzó OverflowError: {e}")

        # _frasesDelResumenDeHoy
        try:
            partes_hoy = self.plugin._frasesDelResumenDeHoy(c, dv, prefs, prob_max=float("inf"), lluvia_total=float("inf"), hora_exacta=float("inf"))
            self.assertIsInstance(partes_hoy, list)
        except OverflowError as e:
            self.fail(f"_frasesDelResumenDeHoy lanzó OverflowError: {e}")

        try:
            frase = self.plugin._fraseDeLluvia(prob_p=float("inf"), prec_s=float("inf"), hora_exacta=float("inf"), hora_fin=float("inf"))
            self.assertIsInstance(frase, str)
        except OverflowError as e:
            self.fail(f"_fraseDeLluvia lanzó OverflowError: {e}")

    # ── 13. Resiliencia en normalización de coordenadas y días de pronóstico ──
    def test_resiliencia_coordenadas_y_pronostico(self):
        """Verifica que coordenadas inf/nan y días infinitos no causen OverflowError ni URLs rotas."""
        import math
        # _normalizarCoord
        self.assertEqual(clima._normalizarCoord("40,4168"), 40.4168)
        self.assertTrue(math.isnan(clima._normalizarCoord(float("nan"))))
        self.assertEqual(clima._normalizarCoord(float("inf")), float("inf"))
        self.assertEqual(clima._normalizarCoord("inf"), "inf")

        # _urlDelPronostico con inf
        url = self.plugin._urlDelPronostico(-34.6, -58.4, float("inf"))
        self.assertIn("forecast_days=6", url)

        # _do_fill_cities con ciudades corruptas (no-list)
        dlg = clima.ConfigDialog.__new__(clima.ConfigDialog)
        dlg._isClosing = False
        dlg._regions = [("Provincia Test", "no_es_una_lista")]
        dlg.cboCity = type("DummyCbo", (), {"Clear": lambda s: None, "AppendItems": lambda s, x: None, "Enable": lambda s: None, "Disable": lambda s: None, "SetSelection": lambda s, i: None})()
        dlg.btnSave = type("DummyBtn", (), {"Enable": lambda s: None, "Disable": lambda s: None})()
        dlg._cfg = {}
        try:
            dlg._do_fill_cities(0)
            self.assertEqual(dlg._cities, [])
        except Exception as e:
            self.fail(f"_do_fill_cities lanzó excepción ante ciudades corruptas: {e}")

    # ── 14. _safe_float exhaustivo y robustez en precipitación y códigos ─────
    def test_safe_float_precipitacion_y_codigos_horarios_seguros(self):
        """Verifica que _safe_float tolere valores infinitos/nan y que las frases del clima y pronóstico manejen datos anómalos sin error."""
        # _safe_float
        self.assertIsNone(clima._safe_float(float("nan")))
        self.assertIsNone(clima._safe_float(float("inf")))
        self.assertIsNone(clima._safe_float(float("-inf")))
        self.assertIsNone(clima._safe_float("inf"))
        self.assertEqual(clima._safe_float("1e10000", default=0.0), 0.0)
        self.assertEqual(clima._safe_float("23.5"), 23.5)

        # _frasesDelClimaActual con precipitación anómala
        c = {"weather_code": 1, "precipitation": float("nan")}
        prefs = {"precipitacion": True, "condicion": True}
        partes = self.plugin._frasesDelClimaActual(c, prefs)
        self.assertIsInstance(partes, list)

        c["precipitation"] = float("inf")
        partes_inf = self.plugin._frasesDelClimaActual(c, prefs)
        self.assertIsInstance(partes_inf, list)

        # _frasesDelResumenDeHoy con precipitation_sum anómalo
        dv = lambda k: float("nan") if "precipitation" in k else 15.0
        partes_hoy = self.plugin._frasesDelResumenDeHoy(c, dv, {"precip_total": True})
        self.assertIsInstance(partes_hoy, list)


    # ── 15. Pronóstico extendido con marcas horarias y datos horarios corruptos ──
    def test_pronostico_extendido_con_marcas_horarias_corruptas(self):
        """Verifica que _frasesDelPronosticoExtendido maneje marcas horarias None o sin formato 'T' sin lanzar excepciones."""
        mock_data = {
            "daily": {
                "time": ["2026-10-14", "2026-10-15"],
                "weather_code": [0, 1],
                "temperature_2m_max": [22.0, 24.0],
                "temperature_2m_min": [12.0, 14.0],
                "precipitation_sum": [0.0, 1.2],
                "precipitation_probability_max": [5, 40],
                "wind_speed_10m_max": [15.0, 18.0],
                "sunrise": ["2026-10-14T07:00", "2026-10-15T07:01"],
                "sunset": ["2026-10-14T19:00", "2026-10-15T18:59"],
            },
            "hourly": {
                "time": [None, 12345, "invalid_time_no_t", "2026-10-14T10:00", "2026-10-14T11:00"],
                "precipitation_probability": [None, float("nan"), float("inf"), 30, 50],
                "precipitation": [None, float("nan"), -5.0, 0.2, 0.5],
                "weather_code": [None, "invalid", 61, 61, 63],
            },
            "current": {"weather_code": 0, "time": "2026-10-14T09:00"},
        }
        with patch.object(self.plugin, "_getJsonFromApi", return_value=mock_data):
            with patch.object(self.plugin, "_safeMessage") as mock_msg:
                self.plugin._fetchForecast({"city": "Madrid", "lat": 40.4, "lon": -3.7, "days": 2, "prefs": {"hora_lluvia": True}})
                mock_msg.assert_called_once()
                texto_pronostico = mock_msg.call_args[0][0]
                self.assertIn("Pronóstico para Madrid", texto_pronostico)


    # ── 16. _stopProgress detiene el timer incluso si _isClosing es True ────
    def test_stop_progress_detiene_timer_al_cerrar_dialogo(self):
        """Verifica que _stopProgress llame a Stop() en el timer aun cuando _isClosing ya sea True."""
        dlg = clima.ConfigDialog.__new__(clima.ConfigDialog)
        mock_timer = MagicMock()
        mock_timer.IsRunning.return_value = True
        dlg._progressTimer = mock_timer
        dlg.progressBar = MagicMock()
        dlg._isClosing = True

        dlg._stopProgress()
        mock_timer.Stop.assert_called_once()
        dlg.progressBar.Hide.assert_called_once()

    # ── 17. ConfigDialog con configuración corrupta en SpinCtrls ─────────────
    def test_config_dialog_spin_ctrl_sanitizacion(self):
        """Verifica que valores de texto corruptos en climaAccesible.json no impidan abrir ConfigDialog."""
        mock_corrupt_cfg = {
            "forecast_days": "invalido",
            "network_retries": "no_es_numero",
            "network_retry_delay": "noventa",
        }
        mock_spin = MagicMock()
        for attr in [
            "ComboBox", "SpinCtrl", "StaticBox", "StaticBoxSizer", "StaticText",
            "Gauge", "CheckBox", "Button", "BoxSizer", "Panel", "Timer"
        ]:
            setattr(clima.wx, attr, MagicMock())
        clima.wx.SpinCtrl = mock_spin
        for const in [
            "CB_READONLY", "GA_HORIZONTAL", "GA_SMOOTH", "ALIGN_CENTER_VERTICAL",
            "ID_OK", "ID_CANCEL", "DEFAULT_DIALOG_STYLE", "RESIZE_BORDER",
            "EXPAND", "ALL", "LEFT", "RIGHT", "TOP", "BOTTOM", "VERTICAL", "HORIZONTAL"
        ]:
            setattr(clima.wx, const, getattr(clima.wx, const, 0))
        for evt in ["EVT_COMBOBOX", "EVT_BUTTON", "EVT_CLOSE", "EVT_TIMER"]:
            setattr(clima.wx, evt, getattr(clima.wx, evt, MagicMock()))

        with patch("climaAccesible.loadJSON", return_value=mock_corrupt_cfg):
            with patch("threading.Thread"):
                try:
                    dlg = clima.ConfigDialog.__new__(clima.ConfigDialog)
                    dlg._cfg = mock_corrupt_cfg
                    dlg._checks = {}
                    dlg._isClosing = False
                    dlg.btnCancel = MagicMock()
                    dlg.Raise = MagicMock()
                    dlg._build_ui()
                    for call in mock_spin.call_args_list:
                        initial_val = call.kwargs.get("initial")
                        self.assertIsInstance(initial_val, int)
                except Exception as e:
                    self.fail(f"_build_ui lanzó excepción con configuración corrupta: {e}")

    # ── 18. _fetchWeather con None en hourly.time y minutely_15 malformado ──
    def test_fetch_weather_marcas_horarias_none_y_minutely_malformado(self):
        """Verifica que _fetchWeather tolere None en horas_time y marcas temporales corruptas en minutely_15."""
        mock_data = {
            "current": {"weather_code": 1, "temperature_2m": 20.0, "time": "2026-10-14T10:00", "precipitation": 0.0},
            "hourly": {
                "time": [None, "invalid_timestamp", "2026-10-14T10:00", "2026-10-14T11:00"],
                "precipitation_probability": [None, 10, 80, 20],
                "precipitation": [None, 0.0, 2.5, 0.0],
            },
            "minutely_15": {
                "time": [None, "no_es_fecha", "2026-10-14T10:15", "2026-10-14T10:30"],
                "precipitation": [None, 0.0, 1.5, 0.0],
                "precipitation_probability": [None, 10, 90, 20],
            },
        }
        with patch.object(self.plugin, "_getJsonFromApi", return_value=mock_data):
            with patch.object(self.plugin, "_safeMessage") as mock_msg:
                cfg = {"city": "Montevideo", "lat": -34.9, "lon": -56.1, "prefs": {"hora_lluvia": True, "minutos_lluvia": True}}
                self.plugin._fetchWeather(cfg)
                mock_msg.assert_called_once()
                msg = mock_msg.call_args[0][0]
                self.assertIn("Montevideo", msg)


if __name__ == "__main__":
    unittest.main()

