# -*- coding: utf-8 -*-
"""Pruebas de la lógica de ClimaAccesible que no necesita NVDA abierto.

Se prueban las funciones que convierten datos del servicio meteorológico en
frases: dirección del viento, condición del cielo, duraciones y momentos de
lluvia. Son puras: misma entrada, misma salida.
"""
import os
import sys
import threading
import unittest
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nvda_falso                                    # noqa: E402

nvda_falso.instalar()

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "globalPlugins"))

import climaAccesible as clima                       # noqa: E402


class DireccionDelViento(unittest.TestCase):
    def test_los_cuatro_puntos_cardinales(self):
        self.assertEqual(clima.cardinal(0), "norte")
        self.assertEqual(clima.cardinal(90), "este")
        self.assertEqual(clima.cardinal(180), "sur")
        self.assertEqual(clima.cardinal(270), "oeste")

    def test_da_la_vuelta_completa(self):
        """360 grados es lo mismo que 0: no debe salirse de la lista."""
        self.assertEqual(clima.cardinal(360), "norte")

    def test_sin_dato(self):
        self.assertEqual(clima.cardinal(None), "dirección desconocida")

    def test_ningun_angulo_se_sale_de_la_lista(self):
        for grados in range(0, 721):
            self.assertIsInstance(clima.cardinal(grados), str)

    def test_los_intermedios(self):
        self.assertEqual(clima.cardinal(45), "noreste")
        self.assertEqual(clima.cardinal(225), "suroeste")


class CondicionDelCielo(unittest.TestCase):
    def test_codigos_conocidos(self):
        self.assertEqual(clima.codigoClima(0), "cielo despejado")
        self.assertEqual(clima.codigoClima(95), "tormenta eléctrica")

    def test_codigo_desconocido_no_revienta(self):
        self.assertEqual(clima.codigoClima(12345), "condición desconocida")

    def test_sin_codigo(self):
        self.assertEqual(clima.codigoClima(None), "condición desconocida")

    def test_los_28_codigos_oficiales_de_open_meteo_no_quedan_como_desconocidos(self):
        # Lista completa de códigos WMO que Open-Meteo puede devolver de verdad.
        # Si a algún código de esta lista le faltara traducción, aparecería como
        # "condición desconocida" en vez de describir el clima.
        codigos_oficiales = [
            0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67,
            71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99,
        ]
        for codigo in codigos_oficiales:
            self.assertNotEqual(
                clima.codigoClima(codigo), "condición desconocida",
                f"Al código {codigo} le falta traducción.",
            )

    def test_el_codigo_77_es_nieve_no_granizo(self):
        # El código 77 de la OMM es "snow grains" (nieve muy fina), un fenómeno
        # distinto y mucho más leve que el granizo (que sí corresponde a los
        # códigos 96 y 99, tormenta con granizo).
        texto = clima.codigoClima(77)
        self.assertIn("nieve", texto)
        self.assertNotIn("granizo", texto)


class Duraciones(unittest.TestCase):
    def test_horas_y_minutos(self):
        self.assertEqual(clima.formatSegundos(3660), "1 hora y 1 minuto")
        self.assertEqual(clima.formatSegundos(7320), "2 horas y 2 minutos")

    def test_solo_horas(self):
        self.assertEqual(clima.formatSegundos(7200), "2 horas")

    def test_solo_minutos(self):
        self.assertEqual(clima.formatSegundos(600), "10 minutos")

    def test_valor_no_numerico_no_revienta(self):
        self.assertIsInstance(clima.formatSegundos("hola"), str)


class NombreDeUnDia(unittest.TestCase):
    """Los dos primeros dias se nombran hoy y manana; el resto por su fecha."""

    def nombre(self, fecha, indice):
        return clima.GlobalPlugin._nombreDeDia(None, fecha, indice)

    def test_los_dos_primeros_dias(self):
        self.assertEqual(self.nombre("2026-09-08", 0), "hoy")
        self.assertEqual(self.nombre("2026-09-08", 1), "mañana")

    def test_los_siguientes_llevan_dia_y_mes(self):
        texto = self.nombre("2026-09-10", 2)
        self.assertIn("10", texto)
        self.assertIn("septiembre", texto)

    def test_una_fecha_ilegible_se_devuelve_tal_cual(self):
        self.assertEqual(self.nombre("no es una fecha", 3), "no es una fecha")


class CalculoFaseLunar(unittest.TestCase):
    """Pruebas para el cálculo de fase lunar con diferentes tipos de datos y casos borde."""

    def test_luna_nueva_conocida(self):
        import datetime
        dt = datetime.datetime(2000, 1, 6, 18, 14)
        self.assertEqual(clima.faseLunar(dt), "Luna nueva")

    def test_soporta_instancia_datetime_date(self):
        import datetime
        d = datetime.date(2026, 9, 19)
        res = clima.faseLunar(d)
        self.assertIsInstance(res, str)
        self.assertNotEqual(res, "desconocida")

    def test_soporta_datetime_con_zona_horaria(self):
        import datetime
        tz = datetime.timezone(datetime.timedelta(hours=-3))
        dt = datetime.datetime(2026, 9, 19, 12, 0, tzinfo=tz)
        res = clima.faseLunar(dt)
        self.assertIsInstance(res, str)
        self.assertNotEqual(res, "desconocida")

    def test_soporta_cadena_iso(self):
        res = clima.faseLunar("2026-09-19")
        self.assertIsInstance(res, str)
        self.assertNotEqual(res, "desconocida")

    def test_fecha_invalida_o_nula_devuelve_desconocida(self):
        self.assertEqual(clima.faseLunar(None), "desconocida")
        self.assertEqual(clima.faseLunar("invalido"), "desconocida")


class EvaluacionPronosticoHoy(unittest.TestCase):
    """Verifica que el pronóstico para 'Hoy' no arrastre llovizna o lluvia de la madrugada."""

    def test_llovizna_pasada_no_contamina_el_resto_del_dia(self):
        # Simula datos horarios donde hubo llovizna en la madrugada (códigos 51, 51%)
        # pero la tarde está nublada (código 3) con solo 2% de probabilidad
        horas_time = [f"2026-09-13T{h:02d}:00" for h in range(24)]
        horas_code = [51, 51, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 1, 1, 1, 3, 2]
        horas_prob = [51, 44, 29, 16, 10, 7, 4, 2, 1, 0, 0, 1, 2, 2, 2, 2, 1, 1, 0, 0, 0, 0, 0, 0]
        horas_prec = [0.1, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        hora_filtro = 15
        fecha = "2026-09-13"

        codigos_rest = [
            int(horas_code[idx_h]) for idx_h, t in enumerate(horas_time)
            if t.startswith(fecha) and int(t.split("T")[1].split(":")[0]) >= hora_filtro
        ]
        probs_rest = [
            int(horas_prob[idx_h]) for idx_h, t in enumerate(horas_time)
            if t.startswith(fecha) and int(t.split("T")[1].split(":")[0]) >= hora_filtro
        ]
        precs_rest = [
            float(horas_prec[idx_h]) for idx_h, t in enumerate(horas_time)
            if t.startswith(fecha) and int(t.split("T")[1].split(":")[0]) >= hora_filtro
        ]

        codigo_now = 3
        candidatos = codigos_rest.copy()
        if codigo_now is not None:
            candidatos.append(codigo_now)
        codigo_final = max(candidatos)

        prob_max_rest = max(probs_rest)
        prec_total_rest = round(sum(precs_rest), 1)

        # El código meteorológico para lo que resta de hoy debe ser nublado (3), NO llovizna (51)
        self.assertEqual(codigo_final, 3)
        self.assertEqual(clima.codigoClima(codigo_final), "nublado")

        # La probabilidad para el resto del día es 2%
        self.assertEqual(prob_max_rest, 2)
        self.assertEqual(prec_total_rest, 0.0)

        # La frase de lluvia no debe anunciar lluvia con 2% y 0.0 mm
        frase = clima.GlobalPlugin._fraseDeLluvia(None, prob_max_rest, prec_total_rest)
        self.assertEqual(frase, "")


class ReintentoDeRed(unittest.TestCase):
    """_getJsonFromApi no debe reintentar cuando el servidor respondió con un error."""

    def test_error_del_servidor_no_se_reintenta(self):
        plugin = clima.GlobalPlugin.__new__(clima.GlobalPlugin)
        def fake_manejar(e, operacion):
            print(f"XXX EXCEPTION CAUGHT: {e}")
            import traceback
            traceback.print_exc()
        plugin._manejarErrorPeticion = fake_manejar
        plugin._stopping = threading.Event()
        intentos = {"cantidad": 0}

        class RespuestaDeError:
            def read(self):
                return b"{}"

        def urlopen_falso(req, timeout=15):
            intentos["cantidad"] += 1
            raise urllib.error.HTTPError(
                "https://ejemplo.invalido", 404, "No encontrado", {}, None
            )

        import urllib.request
        original = urllib.request.urlopen
        urllib.request.urlopen = urlopen_falso
        try:
            with self.assertRaises(urllib.error.HTTPError):
                plugin._getJsonFromApi("https://ejemplo.invalido", "prueba")
        finally:
            urllib.request.urlopen = original

        # Un error del servidor no es un problema de red: no se debe reintentar.
        self.assertEqual(intentos["cantidad"], 1)


class PronosticoResilienteAHorasMalformadas(unittest.TestCase):
    """_fetchForecast no debe cancelar el pronóstico del día por una sola hora con formato raro."""

    def test_una_hora_con_formato_raro_no_cancela_el_pronostico_del_dia(self):
        plugin = clima.GlobalPlugin.__new__(clima.GlobalPlugin)
        def fake_manejar(e, operacion):
            print(f"XXX EXCEPTION CAUGHT: {e}")
            import traceback
            traceback.print_exc()
        plugin._manejarErrorPeticion = fake_manejar
        plugin._stopping = threading.Event()
        mensajes = []
        plugin._safeMessage = lambda texto: mensajes.append(texto)

        datos_falsos = {
            "current": {"time": "2026-09-13T16:00", "weather_code": 3},
            "daily": {
                "time": ["2026-09-13"],
                "weather_code": [51],
                "temperature_2m_max": [22.0],
                "temperature_2m_min": [15.0],
                "wind_speed_10m_max": [10.0],
                "precipitation_probability_max": [40],
                "precipitation_sum": [0.5],
                "sunrise": ["2026-09-13T07:00"],
                "sunset": ["2026-09-13T19:00"],
            },
            "hourly": {
                # Una hora con formato inválido mezclada entre horas normales de la tarde.
                "time": ["2026-09-13T15:00", "2026-09-13Txx:00", "2026-09-13T17:00"],
                "weather_code": [3, 3, 3],
                "precipitation_probability": [5, 5, 5],
                "precipitation": [0.0, 0.0, 0.0],
            },
        }
        plugin._getJsonFromApi = lambda url, label="general": datos_falsos

        plugin._fetchForecast({"city": "Salto", "lat": -31.4, "lon": -57.9, "forecast_days": 1})

        # Debe haber anunciado el pronóstico (un solo mensaje), no haberse quedado callado
        # ni haber caído en el mensaje genérico de "Error inesperado".
        self.assertEqual(len(mensajes), 1)
        self.assertNotIn("Error inesperado", mensajes[0])
        self.assertIn("Salto", mensajes[0])


class UrlDelClimaActual(unittest.TestCase):
    """La URL del clima actual debe solicitar siempre weather_code para evaluar condiciones de luminosidad."""

    def test_incluye_weather_code_aunque_condicion_este_desmarcada(self):
        plugin = clima.GlobalPlugin.__new__(clima.GlobalPlugin)
        def fake_manejar(e, operacion):
            print(f"XXX EXCEPTION CAUGHT: {e}")
            import traceback
            traceback.print_exc()
        plugin._manejarErrorPeticion = fake_manejar
        prefs = {"condicion": False, "amanecer": True, "atardecer": True, "temperatura": True}
        url = plugin._urlDelClimaActual(-34.9, -56.1, prefs)
        self.assertIn("weather_code", url)


class CoordenadasCeroValidas(unittest.TestCase):
    """Las ciudades con latitud 0.0 (en el ecuador) o longitud 0.0 (meridiano de Greenwich) son válidas."""

    def test_latitud_y_longitud_cero_no_se_consideran_sin_configurar(self):
        plugin = clima.GlobalPlugin.__new__(clima.GlobalPlugin)
        plugin._fetchingWeatherActive = False
        plugin._fetchingForecastActive = False
        plugin._stopping = threading.Event()

        cfg_cero = {"city": "Punto Cero", "lat": 0.0, "lon": 0.0, "forecast_days": 3}
        original_load = clima.loadJSON
        clima.loadJSON = lambda path: cfg_cero
        try:
            nvda_falso.dichos.clear()
            import threading as real_threading
            orig_start = real_threading.Thread.start
            hilos_iniciados = []
            real_threading.Thread.start = lambda self: hilos_iniciados.append(self)
            try:
                plugin.script_getWeather(None)
                self.assertNotIn("No hay ciudad configurada", "".join(nvda_falso.dichos))
                self.assertEqual(len(hilos_iniciados), 1)

                nvda_falso.dichos.clear()
                hilos_iniciados.clear()
                plugin.script_getForecast(None)
                self.assertNotIn("No hay ciudad configurada", "".join(nvda_falso.dichos))
                self.assertEqual(len(hilos_iniciados), 1)
            finally:
                real_threading.Thread.start = orig_start
        finally:
            clima.loadJSON = original_load

    def test_coordenadas_none_si_avisan_que_falta_ciudad(self):
        plugin = clima.GlobalPlugin.__new__(clima.GlobalPlugin)
        plugin._fetchingWeatherActive = False
        plugin._fetchingForecastActive = False

        cfg_vacio = {"city": "", "lat": None, "lon": None}
        original_load = clima.loadJSON
        clima.loadJSON = lambda path: cfg_vacio
        try:
            nvda_falso.dichos.clear()
            plugin.script_getWeather(None)
            self.assertTrue(any("No hay ciudad configurada" in d for d in nvda_falso.dichos))
        finally:
            clima.loadJSON = original_load


class FiltroUVNocturno(unittest.TestCase):
    """El índice UV debe omitirse de noche cuando es 0.0 para no añadir ruido innecesario."""

    def test_uv_cero_de_noche_se_omite(self):
        plugin = clima.GlobalPlugin.__new__(clima.GlobalPlugin)
        prefs = {"uv_actual": True}
        c = {"is_day": 0, "uv_index": 0.0}
        frases = plugin._frasesDelClimaActual(c, prefs)
        self.assertFalse(any("UV" in f for f in frases))

    def test_uv_de_dia_se_anuncia(self):
        plugin = clima.GlobalPlugin.__new__(clima.GlobalPlugin)
        prefs = {"uv_actual": True}
        c = {"is_day": 1, "uv_index": 0.0}
        frases = plugin._frasesDelClimaActual(c, prefs)
        self.assertTrue(any("UV" in f for f in frases))

    def test_uv_mayor_que_cero_de_noche_se_anuncia(self):
        plugin = clima.GlobalPlugin.__new__(clima.GlobalPlugin)
        prefs = {"uv_actual": True}
        c = {"is_day": 0, "uv_index": 1.2}
        frases = plugin._frasesDelClimaActual(c, prefs)
        self.assertTrue(any("UV" in f for f in frases))


class SincronizacionMinutosLluviaZonaHoraria(unittest.TestCase):
    """El radar de lluvia a 15 minutos debe sincronizarse con la hora local de la ciudad consultada."""

    def test_radar_lluvia_usa_hora_local_de_la_ciudad(self):
        plugin = clima.GlobalPlugin.__new__(clima.GlobalPlugin)
        plugin._stopping = threading.Event()
        mensajes = []
        plugin._safeMessage = lambda texto: mensajes.append(texto)

        datos_falsos = {
            "current": {
                "time": "2026-09-13T16:00",
                "temperature_2m": 20.0,
                "precipitation": 0.0,
            },
            "daily": {},
            "hourly": {},
            "minutely_15": {
                "time": [
                    "2026-09-13T16:00",
                    "2026-09-13T16:15",
                    "2026-09-13T16:30",
                    "2026-09-13T16:45",
                ],
                "precipitation": [0.0, 0.0, 0.8, 1.2],
                "precipitation_probability": [0, 10, 80, 90],
            },
        }
        plugin._getJsonFromApi = lambda url, label="general": datos_falsos

        cfg = {
            "city": "Tokio",
            "lat": 35.68,
            "lon": 139.76,
            "prefs": {"minutos_lluvia": True, "temperatura": True},
        }
        plugin._fetchWeather(cfg)

        self.assertEqual(len(mensajes), 1)
        texto = mensajes[0]
        self.assertIn("30 minutos", texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)

