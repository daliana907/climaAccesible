# -*- coding: utf-8 -*-
# Accessible Weather (ClimaAccesible) for NVDA
#
# Real-time weather and extended forecast add-on using the open Open-Meteo API.
# Inspired by the concept of Weather Plus by Adriano Barbieri and contributors.
# Rewritten, modernized and maintained as ClimaAccesible by Daliana (2025-2026).
# Released under the GNU General Public License version 2 (GPLv2).
#
# Shortcuts: NVDA+W = current weather | NVDA+Shift+W = forecast | NVDA+Control+W = settings


import globalPluginHandler
import scriptHandler
import ui
import threading
import urllib.request
import urllib.error
import json
import wx
import addonHandler
addonHandler.initTranslation()
import gui
import os
import re
import time  # Necesario para medir latencias y tiempos de respuesta HTTP de Open-Meteo
import datetime
import socket
import math
import globalVars
import core
from logHandler import log

import urllib.parse
import unicodedata
import shutil
try:
	from builtins import ngettext as _ngettext
except ImportError:
	_ngettext = None
if _ngettext is None:
	try:
		_ngettext = ngettext  # noqa: F821 - provisto por NVDA en tiempo de ejecucion
	except NameError:
		def _ngettext(singular, plural, n):
			return singular if n == 1 else plural

_wxDead = getattr(wx, "PyDeadObjectError", None)
DeadErrors = (_wxDead,) if isinstance(_wxDead, type) and issubclass(_wxDead, BaseException) else ()
# Compatibilidad: nombre historico usado en varios except.
DeadObjectError = DeadErrors if DeadErrors else (RuntimeError,)

def _esObjetoDestruido(exc):
	"""True si la excepcion indica objeto wx C++ ya destruido."""
	try:
		if DeadErrors and isinstance(exc, DeadErrors):
			return True
	except Exception as _e:
		log.debugWarning("ClimaAccesible: _esObjetoDestruido check fallo: {}".format(_e), exc_info=True)
	try:
		return "deleted" in str(exc).lower()
	except Exception as _e:
		log.debugWarning("ClimaAccesible: _esObjetoDestruido str fallo: {}".format(_e), exc_info=True)
		return False

# ── rutas de archivos ─────────────────────────────────────────────────────────
_ADDON_DIR   = os.path.dirname(__file__)
GEODATA_FILE = os.path.join(_ADDON_DIR, "geodata.json")

def _configPath():
	"""Devuelve la ruta correcta para guardar la configuración en el perfil de NVDA."""
	configDir = getattr(getattr(globalVars, "appArgs", None), "configPath", None)
	if not configDir:
		import tempfile
		configDir = tempfile.gettempdir()
		log.warning("ClimaAccesible: configPath no disponible, usando temporal (no persistente).")
	return os.path.join(configDir, "climaAccesible.json")

# ── caché de datos geográficos ────────────────────────────────────────────────
_geoData = None
_geoDataLock = threading.Lock()
_geoIndex = {}
_geoSortedCache = {}

# ── caché API 5min + debounce 2s ──────────────────────────────────────────────
_API_CACHE = {}
_API_CACHE_TTL = 300
_API_DEBOUNCE = 2.0
_apiCacheLock = threading.Lock()

# Aviso único por sesión cuando la config está corrupta y se aplican valores por defecto.
_CORRUPT_NOTIFIED = False


def _notify_corruption_once(path, reason):
	"""Anuncia una sola vez por sesión que la config estaba corrupta y se usan valores por defecto."""
	global _CORRUPT_NOTIFIED
	try:
		log.warning("ClimaAccesible: config corrupta en {} ({}); se aplican valores por defecto.".format(path, reason))
	except Exception:
		pass
	if _CORRUPT_NOTIFIED:
		return
	_CORRUPT_NOTIFIED = True
	try:
		import ui as _ui
		msg = _("La configuración del clima estaba dañada. Se restauraron los valores por defecto.")
		try:
			wx.CallAfter(_ui.message, msg)
		except Exception:
			try:
				_ui.message(msg)
			except Exception:
				pass
	except Exception:
		pass

def _normTxt(s):
	"""Normaliza texto para ordenar/filtrar: NFKD + casefold, seguro ante None."""
	try:
		t = unicodedata.normalize("NFKD", str(s))
		return t.casefold()
	except Exception as _e:
		log.debugWarning("ClimaAccesible: _normTxt fallo: {}".format(_e), exc_info=True)
		try:
			return str(s).casefold()
		except Exception as _e2:
			log.debugWarning("ClimaAccesible: _normTxt fallback fallo: {}".format(_e2), exc_info=True)
			return ""

# ── opciones de datos del clima ───────────────────────────────────────────────
def N_(texto):
	"""Marca un texto para que el extractor de traducciones lo recoja.

	Se usa en las tablas que se crean al cargar el complemento: ahí no se puede
	traducir todavía, así que se traduce con _() en el momento de mostrarlo.
	"""
	return texto


def _safe_float(val, default=None):
	"""Convierte un valor a float de manera segura sin lanzar excepciones."""
	if val is None:
		return default
	try:
		if isinstance(val, str):
			val = val.strip().replace(",", ".")
		f = float(val)
		if math.isnan(f) or math.isinf(f):
			return default
		return f
	except (ValueError, TypeError, OverflowError):
		return default


def _coord_valida(lat, lon):
	"""Valida coordenadas y devuelve (lat, lon) como float. Lanza ValueError si no son válidas."""
	if lat is None or lon is None:
		raise ValueError("coordenadas ausentes")
	lat_f = _safe_float(lat, default=None)
	lon_f = _safe_float(lon, default=None)
	if lat_f is None or lon_f is None:
		raise ValueError("coordenadas no numéricas")
	if not (math.isfinite(lat_f) and math.isfinite(lon_f)):
		raise ValueError("coordenadas no finitas")
	if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
		raise ValueError("coordenadas fuera de rango")
	return (lat_f, lon_f)


OPCIONES = [
	# (clave, etiqueta, campo_api, tipo)
	("temperatura",     N_("Temperatura actual"),                       "temperature_2m",                "current"),
	("sensacion",       N_("Sensación térmica"),                        "apparent_temperature",           "current"),
	("condicion",       N_("Condición del cielo"),                      "weather_code",                   "current"),
	("es_dia",          N_("Si es de día o de noche"),                  "is_day",                         "current"),
	("humedad",         N_("Humedad"),                                  "relative_humidity_2m",           "current"),
	("punto_rocio",     N_("Punto de rocío"),                           "dew_point_2m",                   "current"),
	("viento_vel",      N_("Velocidad del viento"),                     "wind_speed_10m",                 "current"),
	("viento_dir",      N_("Dirección del viento"),                     "wind_direction_10m",             "current"),
	("viento_rafagas",  N_("Ráfagas de viento"),                        "wind_gusts_10m",                 "current"),
	("nubosidad",       N_("Nubosidad"),                                "cloud_cover",                    "current"),
	("precipitacion",   N_("Precipitación actual (lluvia general)"),    "precipitation",                  "current"),
	("nieve",           N_("Nevada actual y espesor de nieve"),         "snowfall",                       "current"),  # Usa snowfall y pide snow_depth
	("visibilidad",     N_("Visibilidad actual"),                       "visibility",                     "current"),
	("uv_actual",       N_("Índice UV en tiempo real"),                 "uv_index",                       "current"),
	("presion",         N_("Presión atmosférica"),                      "surface_pressure",               "current"),
	("luna",            N_("Fases de la luna"),                         "moon_phase",                     "special"),
	("elevacion",       N_("Elevación sobre el nivel del mar"),         "elevation",                      "special"),
	("calidad_aire",    N_("Nivel de contaminación del aire"),           "european_aqi",                   "air_quality"),
	("amanecer",        N_("Hora de salida del sol"),                   "sunrise",                        "daily"),
	("atardecer",       N_("Hora de puesta del sol"),                   "sunset",                         "daily"),
	("uv_max",          N_("Índice UV máximo del día"),                 "uv_index_max",                   "daily"),
	("precip_prob_max", N_("Probabilidad máxima de lluvia del día"),    "precipitation_probability_max", "daily"),
	("precip_total",    N_("Precipitación total esperada del día"),     "precipitation_sum",              "daily"),
	("nieve_total",     N_("Nieve total esperada del día"),             "snowfall_sum",                   "daily"),
	("horas_lluvia",    N_("Horas de lluvia estimadas"),                "precipitation_hours",            "daily"),
	("hora_lluvia",     N_("Aviso de hora exacta de lluvia"),           "rain_hour",                      "special_daily"),
	("minutos_lluvia",  N_("Alerta inminente de lluvia (radar 15 min)"),"rain_minutely",                  "special_current"),
	("viento_max",      N_("Viento máximo del día"),                    "wind_speed_10m_max",             "daily"),
	("rafaga_max",      N_("Ráfaga máxima del día"),                    "wind_gusts_10m_max",             "daily"),
]

PREFS_DEFECTO = {op[0]: True for op in OPCIONES}
PREFS_DEFECTO["network_retries"] = 1
PREFS_DEFECTO["network_retry_delay"] = 1.0


# ── alertas meteorológicas oficiales ──────────────────────────────────────────
# Cada proveedor devuelve datos de su organismo público. No se infieren alertas
# a partir del pronóstico: si un país no tiene proveedor aquí, se dice claramente.
ALERTAS_PROVEEDORES = {
	"UY": {
		"nombre": "INUMET",
		"url": "https://datosuruguay.com/api/v1/weather-alerts",
		"tipo": "uruguay_json",
	},
	"US": {
		"nombre": "National Weather Service",
		"url": "https://api.weather.gov/alerts/active?point={lat:.4f},{lon:.4f}",
		"tipo": "nws_json",
	},
}


def _nivelAlerta(valor):
	"""Convierte niveles oficiales heterogéneos a amarillo, naranja, rojo o aviso."""
	v = _normTxt(valor)
	if any(x in v for x in ("extreme", "red", "roja", "rojo", "alerta roja")):
		return "roja"
	if any(x in v for x in ("severe", "orange", "naranja", "alerta naranja")):
		return "naranja"
	if any(x in v for x in ("moderate", "minor", "yellow", "amarilla", "amarillo", "advisory", "watch")):
		return "amarilla"
	return "aviso"


def _textoCortoAlerta(valor, limite=180):
	"""Limpia texto externo para que una alerta remota no sature la voz."""
	try:
		texto = " ".join(str(valor or "").split())
		return texto[:limite]
	except Exception:
		return ""


def _alertasNWS(data):
	"""Normaliza la respuesta oficial del National Weather Service de EE. UU."""
	resultados = []
	features = data.get("features", []) if isinstance(data, dict) else []
	for feature in features[:10]:
		props = feature.get("properties", {}) if isinstance(feature, dict) else {}
		if not isinstance(props, dict):
			continue
		titulo = _textoCortoAlerta(props.get("headline") or props.get("event"))
		if not titulo:
			continue
		resultados.append({
			"nivel": _nivelAlerta(props.get("severity")),
			"titulo": titulo,
			"zonas": _textoCortoAlerta(props.get("areaDesc"), 120),
			"inicio": _textoCortoAlerta(props.get("onset") or props.get("effective"), 40),
			"fin": _textoCortoAlerta(props.get("ends") or props.get("expires"), 40),
			"detalle": _textoCortoAlerta(props.get("description"), 220),
		})
	return resultados


def _alertasUruguay(data):
	"""Normaliza la API pública que redistribuye las alertas de INUMET.

	El servicio puede cambiar los nombres de sus campos; por eso se aceptan las
	variantes habituales y se ignoran registros incompletos en vez de inventar datos.
	"""
	if isinstance(data, dict):
		items = data.get("data", data.get("alerts", data.get("results", [])))
	elif isinstance(data, list):
		items = data
	else:
		items = []
	if not isinstance(items, list):
		return []
	resultados = []
	for item in items[:10]:
		if not isinstance(item, dict):
			continue
		titulo = _textoCortoAlerta(item.get("title") or item.get("headline") or item.get("phenomenon") or item.get("event"))
		detalle = _textoCortoAlerta(item.get("description") or item.get("detail") or item.get("message"))
		if not titulo and not detalle:
			continue
		resultados.append({
			"nivel": _nivelAlerta(item.get("level") or item.get("color") or item.get("severity")),
			"titulo": titulo or detalle,
			"zonas": _textoCortoAlerta(item.get("areas") or item.get("area") or item.get("departments"), 120),
			"inicio": _textoCortoAlerta(item.get("start") or item.get("onset") or item.get("effective"), 40),
			"fin": _textoCortoAlerta(item.get("end") or item.get("expires") or item.get("until"), 40),
			"detalle": detalle,
		})
	return resultados


def _resumenAlertas(alertas, fuente):
	"""Devuelve un mensaje breve y accesible, limitado a tres alertas."""
	if not alertas:
		return _("No hay alertas meteorológicas oficiales vigentes según {}.").format(fuente)
	partes = []
	for alerta in alertas[:3]:
		titulo = _textoCortoAlerta(alerta.get("titulo")) or _("Alerta meteorológica")
		parte = _("Alerta {nivel}: {titulo}.").format(nivel=alerta.get("nivel", "aviso"), titulo=titulo)
		zonas = _textoCortoAlerta(alerta.get("zonas"))
		if zonas:
			parte += " " + _("Zonas: {}.").format(zonas)
		fin = _textoCortoAlerta(alerta.get("fin"))
		if fin:
			parte += " " + _("Hasta: {}.").format(fin)
		partes.append(parte)
	if len(alertas) > 3:
		partes.append(_("Hay {} alertas adicionales. Consulta la fuente oficial para el detalle.").format(len(alertas) - 3))
	return " ".join(partes)

# ── helpers ───────────────────────────────────────────────────────────────────

def loadJSON(path):
	"""Carga un archivo JSON desde el disco de forma segura.

	Si el archivo no existe o está corrupto, captura el error, deja una nota
	en el registro de NVDA para no interrumpir al usuario y devuelve un diccionario
	vacío para que el resto del complemento pueda seguir funcionando sin fallar.
	Aborta con backup+{} si supera 1 MB (protección anti-DoS).
	La lectura acepta lat/lon con 8 decimales u otra precisión (compatibilidad).
	"""
	try:
		if os.path.exists(path):
			try:
				if os.path.getsize(path) > 1024 * 1024:
					try:
						shutil.copy(path, path + ".corrupto.bak")
					except Exception as _be:
						log.debugWarning("ClimaAccesible: no se pudo crear backup corrupto: {}".format(_be), exc_info=True)
					_notify_corruption_once(path, "supera 1 MB")
					return {}
			except OSError:
				pass
			try:
				with open(path, "r", encoding="utf-8", errors="replace") as f:
					content = f.read(1024 * 1024 + 1)
					if len(content) > 1024 * 1024:
						try:
							shutil.copy(path, path + ".corrupto.bak")
						except Exception as _be:
							log.debugWarning("ClimaAccesible: no se pudo crear backup corrupto: {}".format(_be), exc_info=True)
						_notify_corruption_once(path, "supera 1 MB")
						return {}
					data = json.loads(content)
			except Exception as e:
				try:
					shutil.copy(path, path + ".corrupto.bak")
				except Exception as _be:
					log.debugWarning("ClimaAccesible: no se pudo crear backup corrupto: {}".format(_be), exc_info=True)
				log.warning("ClimaAccesible: error al leer {}: {}".format(path, e))
				_notify_corruption_once(path, e)
				return {}
			if not isinstance(data, dict):
				try:
					shutil.copy(path, path + ".corrupto.bak")
				except Exception as _be:
					log.debugWarning("ClimaAccesible: no se pudo crear backup corrupto: {}".format(_be), exc_info=True)
				log.warning("ClimaAccesible: JSON no es dict en {}".format(path))
				_notify_corruption_once(path, "JSON no es dict")
				return {}
			# Validar lat/lon si están presentes: deben ser float finitos en rango.
			if "lat" in data or "lon" in data:
				try:
					lat_v = data.get("lat")
					lon_v = data.get("lon")
					if lat_v is not None or lon_v is not None:
						_coord_valida(lat_v, lon_v)
				except ValueError as _ve:
					log.warning("ClimaAccesible: coordenadas inválidas en {}: {}".format(path, _ve))
					_notify_corruption_once(path, _ve)
					return {}
			return data
	except Exception as e:
		log.warning("ClimaAccesible: error al leer {}: {}".format(path, e))
	return {}

def saveJSON(path, data):
	"""Guarda datos en un archivo JSON en el disco con formato legible y codificación UTF-8.

	Usa sangría de dos espacios y asegura que los caracteres con tildes o caracteres
	especiales no se escapen en secuencias raras de Unicode, para que el usuario o
	desarrollador pueda leer el archivo directamente si lo abre.
	Privacidad: redondea lat/lon a 4 decimales (~11 m) al guardar; la lectura
	sigue aceptando 8 decimales u otra precisión por compatibilidad.
	Devuelve True si tuvo éxito, False en caso contrario.
	"""
	try:
		try:
			if isinstance(data, dict):
				data = dict(data)
				for _k in ("lat", "lon"):
					if _k in data and data[_k] is not None:
						try:
							_v = data[_k]
							if isinstance(_v, str):
								_v = _v.strip().replace(",", ".")
							data[_k] = round(float(_v), 4)
						except (ValueError, TypeError, OverflowError):
							pass
		except Exception:
			pass
		tmp = path + ".tmp"
		with open(tmp, "w", encoding="utf-8", errors="replace") as f:
			json.dump(data, f, ensure_ascii=False, indent=2)
			try:
				f.flush()
				os.fsync(f.fileno())
			except Exception as _fe:
				log.debugWarning("ClimaAccesible: fsync fallo: {}".format(_fe), exc_info=True)
		os.replace(tmp, path)
		return True
	except Exception as e:
		log.error("ClimaAccesible: error al guardar {}: {}".format(path, e))
		return False

def _nfcNombre(s):
	"""Normaliza un nombre geográfico a NFC (una sola vez al cargar)."""
	try:
		return unicodedata.normalize("NFC", str(s))
	except Exception:
		return s

def _normalizarGeoData(raw):
	"""Normaliza a NFC una vez y fusiona regiones homónimas (H2/H5).

	Cuando dos regiones del mismo país comparten nombre normalizado
	(p. ej. Cantabria x2 en ES), une sus ciudades deduplicando por
	coordenadas en vez de mostrar la región dos veces.
	"""
	norm = []
	for _c in raw:
		try:
			if not isinstance(_c, (list, tuple)) or len(_c) < 2 or not _c[0]:
				continue
			_cname = _nfcNombre(_c[0])
			_iso = _c[1]
			_states = _c[2] if len(_c) > 2 and isinstance(_c[2], list) else []
			_merged = {}
			_orden = []
			for _s in _states:
				if not isinstance(_s, (list, tuple)) or len(_s) < 1 or not _s[0]:
					continue
				_sname = _nfcNombre(_s[0])
				_key = _normTxt(_sname)
				_sid = _s[1] if len(_s) > 1 else 0
				_cities = _s[2] if len(_s) >= 3 and isinstance(_s[2], list) else []
				_nc = []
				for _ci in _cities:
					if not isinstance(_ci, (list, tuple)) or len(_ci) < 3 or not _ci[0]:
						continue
					_nc.append([_nfcNombre(_ci[0]), _ci[1], _ci[2]])
				if _key not in _merged:
					_merged[_key] = [_sname, _sid, _nc]
					_orden.append(_key)
				else:
					_vistos = {(str(_x[1]).strip(), str(_x[2]).strip()) for _x in _merged[_key][2]}
					for _item in _nc:
						_k2 = (str(_item[1]).strip(), str(_item[2]).strip())
						if _k2 not in _vistos:
							_merged[_key][2].append(_item)
							_vistos.add(_k2)
			norm.append([_cname, _iso, [[_merged[k][0], _merged[k][1], _merged[k][2]] for k in _orden]])
		except Exception as _e:
			log.debugWarning("ClimaAccesible: región ignorada al normalizar: {}".format(_e), exc_info=True)
			continue
	return norm

def getGeoData():
	"""Obtiene la base de datos geográfica local (países, regiones y ciudades).

	Para que la ventana de configuración abra rápido y no lea el disco cada vez,
	mantiene los datos en memoria una vez cargados (patrón Singleton / caché).
	Si todavía no se han leído, abre geodata.json y los carga, normalizando a
	NFC una sola vez y fusionando regiones homónimas. La búsqueda por país usa
	el índice {iso2: posición} y la configuración persiste iso2+lat/lon.
	"""
	global _geoData, _geoIndex
	if _geoData is None:
		with _geoDataLock:
			if _geoData is None:
				try:
					with open(GEODATA_FILE, "r", encoding="utf-8", errors="replace") as f:
						data = json.load(f)
					_geoData = _normalizarGeoData(data if isinstance(data, list) else [])
					# Índice {iso2: idx} para búsqueda O(1) por país.
					try:
						_geoIndex = {}
						for _i, _c in enumerate(_geoData):
							if isinstance(_c, (list, tuple)) and len(_c) >= 2:
								_iso = str(_c[1]) if _c[1] is not None else ""
								if _iso and _iso not in _geoIndex:
									_geoIndex[_iso] = _i
					except Exception as _ie:
						log.debugWarning("ClimaAccesible: no se pudo indexar geodata: {}".format(_ie), exc_info=True)
						_geoIndex = {}
				except Exception as e:
					log.error("ClimaAccesible: no se pudo cargar geodata.json: {}".format(e))
					_geoData = []
					_geoIndex = {}
	return _geoData

def formatHora(iso_str):
	"""Extrae la hora y los minutos de una fecha con formato ISO 8601 (ejemplo: 2026-09-12T14:30).

	Devuelve solo la parte '14:30' para que NVDA la lea de forma clara y limpia sin
	atiborrar al usuario con fechas largas o segundos innecesarios.
	"""
	if not iso_str:
		return _("hora desconocida")
	try:
		s = str(iso_str).replace(" ", "T").strip()
		if "T" in s:
			parts = s.split("T")
			res = parts[1][:5] if len(parts) > 1 else ""
		else:
			res = s[:5]
		res = (res or "").strip()
		if not res:
			return _("hora desconocida")
		# Validar forma HH:MM para no anunciar basura.
		if len(res) == 5 and res[2] == ":" and res[:2].isdigit() and res[3:].isdigit():
			return res
		return _("hora desconocida")
	except Exception as e:
		log.debugWarning("ClimaAccesible: formatHora fallo: {}".format(e), exc_info=True)
		return _("hora desconocida")

def formatSegundos(seg):
	"""Convierte una cantidad de segundos en una frase natural de horas y minutos.

	Por ejemplo, convierte la duración de luz solar en '11 horas y 45 minutos'.
	Si solo son horas completas omite los minutos, y si es menos de una hora solo
	menciona los minutos, para que el sintetizador suene natural al hablar.
	"""
	try:
		seg_num = float(seg)
		if math.isnan(seg_num) or math.isinf(seg_num):
			return ""
		seg = max(0, int(seg_num))
		h   = seg // 3600
		m   = (seg % 3600) // 60
		if h <= 0 and m <= 0:
			return _ngettext("{count} hora", "{count} horas", 0).format(count=0)
		txt_h = _ngettext("{count} hora", "{count} horas", h).format(count=h)
		txt_m = _ngettext("{count} minuto", "{count} minutos", m).format(count=m)
		if h > 0 and m > 0:
			# Translators: Frase que une horas y minutos de luz solar.
			return _("{horas} y {minutos}").format(horas=txt_h, minutos=txt_m)
		elif h > 0:
			return txt_h
		else:
			return txt_m
	except Exception as e:
		log.debugWarning("ClimaAccesible: formatSegundos fallo: {}".format(e), exc_info=True)
		return ""

def faseLunar(date):
	if not date:
		return _("desconocida")
	try:
		if isinstance(date, str):
			try:
				date = datetime.datetime.fromisoformat(date)
			except Exception as e:
				log.debugWarning("ClimaAccesible: faseLunar iso fallback: {}".format(e), exc_info=True)
				date = datetime.datetime.strptime(date[:10], "%Y-%m-%d")
		elif isinstance(date, datetime.date) and not isinstance(date, datetime.datetime):
			date = datetime.datetime.combine(date, datetime.time(12, 0))
		elif isinstance(date, datetime.datetime) and date.tzinfo is not None:
			date = date.replace(tzinfo=None)

		known_new_moon = datetime.datetime(2000, 1, 6, 18, 14)
		days_since = (date - known_new_moon).total_seconds() / 86400.0
		lunar_days = 29.53058770576
		phase = (days_since % lunar_days) / lunar_days

		if phase < 0.03 or phase > 0.97: return _("Luna nueva")
		elif phase < 0.22: return _("Luna creciente")
		elif phase < 0.28: return _("Cuarto creciente")
		elif phase < 0.47: return _("Luna casi llena (creciente)")
		elif phase < 0.53: return _("Luna llena")
		elif phase < 0.72: return _("Luna empezando a menguar")
		elif phase < 0.78: return _("Cuarto menguante")
		else: return _("Luna menguante")
	except Exception as e:
		log.debugWarning("ClimaAccesible: faseLunar fallo: {}".format(e), exc_info=True)
		return _("desconocida")

def cardinal(deg):
	"""Convierte los grados de una veleta (0 a 360) en el punto cardinal correspondiente.

	Divide la rosa de los vientos en 16 sectores de 22.5 grados cada uno (Norte,
	Nor-Noreste, Noreste, etc.) para que quien use el lector de pantalla sepa de
	dónde viene el viento de forma intuitiva sin tener que interpretar números de grados.
	"""
	if deg is None:
		return _("dirección desconocida")
	try:
		deg = float(deg)
		dirs = [
			_("norte"), _("nor noreste"), _("noreste"), _("este noreste"),
			_("este"), _("este sureste"), _("sureste"), _("sur sureste"),
			_("sur"), _("sur suroeste"), _("suroeste"), _("oeste suroeste"),
			_("oeste"), _("oeste noroeste"), _("noroeste"), _("nor noroeste"),
		]
		return dirs[round(deg / 22.5) % 16]
	except Exception as e:
		log.debugWarning("ClimaAccesible: cardinal fallo: {}".format(e), exc_info=True)
		return _("dirección desconocida")

def codigoClima(code):
	"""Traduce el código numérico meteorológico de la OMM (WMO) a una descripción en español.

	Los servicios como Open-Meteo devuelven códigos estándar internacionales
	(por ejemplo: 0 para despejado, 61 para lluvia ligera, 95 para tormenta).
	Esta función los mapea a textos accesibles y comprensibles al oído.
	"""
	try:
		code = int(code)
	except (ValueError, TypeError, OverflowError):
		pass
	m = {
		0:_("cielo despejado"),       1:_("mayormente despejado"),   2:_("parcialmente nublado"),
		3:_("nublado"),               45:_("niebla"),                48:_("niebla con escarcha"),
		51:_("llovizna ligera"),      53:_("llovizna moderada"),     55:_("llovizna densa"),
		56:_("llovizna engelante ligera"), 57:_("llovizna engelante densa"),
		61:_("lluvia ligera"),        63:_("lluvia moderada"),       65:_("lluvia intensa"),
		66:_("lluvia engelante ligera"),   67:_("lluvia engelante intensa"),
		71:_("nevada ligera"),        73:_("nevada moderada"),       75:_("nevada intensa"),
		77:_("granos de nieve"),  80:_("chubascos ligeros"),     81:_("chubascos moderados"),
		82:_("chubascos intensos"),   85:_("chubascos de nieve ligeros"),
		86:_("chubascos de nieve intensos"),
		95:_("tormenta eléctrica"),   96:_("tormenta con granizo ligero"),
		99:_("tormenta con granizo intenso"),
	}
	return m.get(code, _("condición desconocida"))



def uvFrase(uv):
	try:
		u = float(uv)
		if math.isnan(u) or math.isinf(u) or u < 0:
			return ""
		if u <= 2.9: return _("Bajo")
		elif u <= 5.9: return _("Moderado")
		elif u <= 7.9: return _("Alto")
		elif u <= 10.9: return _("Muy alto")
		else: return _("Extremo")
	except Exception as e:
		log.debugWarning("ClimaAccesible: uvFrase fallo: {}".format(e), exc_info=True)
		return ""

def calidadAireFrase(aqi):
	try:
		a = float(aqi)
		if math.isnan(a) or math.isinf(a) or a < 0:
			return ""
		if a <= 20: return _("Bueno")
		elif a <= 40: return _("Aceptable")
		elif a <= 60: return _("Moderado")
		elif a <= 80: return _("Malo")
		elif a <= 100: return _("Muy malo")
		else: return _("Peligroso")
	except Exception as e:
		log.debugWarning("ClimaAccesible: calidadAireFrase fallo: {}".format(e), exc_info=True)
		return ""


# ── diálogo de configuración ──────────────────────────────────────────────────

def _normalizarCoord(coord):
	"""Normaliza una coordenada decimal (reemplaza comas por puntos y elimina espacios)."""
	try:
		val = float(str(coord).strip().replace(",", "."))
		if math.isnan(val) or math.isinf(val):
			return coord
		return val
	except (ValueError, TypeError, OverflowError):
		return coord


class ConfigDialog(wx.Dialog):
	"""Diálogo accesible para configurar la ubicación geográfica y opciones meteorológicas."""

	def __init__(self, parent):
		"""Inicializa el diálogo accesible de configuración, cargando las opciones guardadas."""
		super(ConfigDialog, self).__init__(
			parent,
			title=_("ClimaAccesible - Configuración"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
		)
		self._isClosing = False
		self._destroyed = False
		self._countries = []
		self._regions   = []
		self._cities    = []
		self._cfg       = loadJSON(_configPath())
		self._checks    = {}
		self._build_ui()
		# Sin foco inicial forzado: _populate_countries lo pone en cboCountry al terminar de cargar.
		self.Raise()
		threading.Thread(target=self._load_countries, daemon=True).start()

	def _build_ui(self):
		"""Monta la ventana de configuración, de arriba abajo.

		Primero el apartado Ubicación, con las tres listas encadenadas: país,
		región y ciudad. Luego las casillas de qué datos quieres oír, la casilla
		de cuántos días de pronóstico, y los botones Guardar y Cancelar. Al final
		arranca el temporizador que va diciendo "cargando" mientras se leen los
		países, que son muchos y tardan un momento.
		"""
		p    = wx.Panel(self)
		main = wx.BoxSizer(wx.VERTICAL)

		# ── ubicación ────────────────────────────────────────────────────────
		box_loc   = wx.StaticBox(p, label=_("Ubicación"))
		sizer_loc = wx.StaticBoxSizer(box_loc, wx.VERTICAL)

		sizer_loc.Add(wx.StaticText(p, label=_("&País:")), 0, wx.LEFT|wx.TOP, 4)
		self.cboCountry = wx.ComboBox(p, style=wx.CB_READONLY, size=(420, -1))
		self.cboCountry.SetName(_("País"))
		self.cboCountry.Disable()
		self.cboCountry.Bind(wx.EVT_COMBOBOX, self.onCountryChange)
		sizer_loc.Add(self.cboCountry, 0, wx.LEFT|wx.RIGHT, 4)

		sizer_loc.Add(wx.StaticText(p, label=_("Departamento / &Región:")), 0, wx.LEFT|wx.TOP, 4)
		self.cboRegion = wx.ComboBox(p, style=wx.CB_READONLY, size=(420, -1))
		self.cboRegion.SetName(_("Región"))
		self.cboRegion.Disable()
		self.cboRegion.Bind(wx.EVT_COMBOBOX, self.onRegionChange)
		sizer_loc.Add(self.cboRegion, 0, wx.LEFT|wx.RIGHT, 4)

		sizer_loc.Add(wx.StaticText(p, label=_("&Ciudad:")), 0, wx.LEFT|wx.TOP, 4)
		self.cboCity = wx.ComboBox(p, style=wx.CB_READONLY, size=(420, -1))
		self.cboCity.SetName(_("Ciudad"))
		self.cboCity.Disable()
		self.cboCity.Bind(wx.EVT_COMBOBOX, self.onCityChange)
		sizer_loc.Add(self.cboCity, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 4)

		self.progressBar = wx.Gauge(p, range=100, size=(420, 18), style=wx.GA_HORIZONTAL|wx.GA_SMOOTH)
		self.progressBar.SetName(_("Cargando datos geográficos"))
		sizer_loc.Add(self.progressBar, 0, wx.LEFT|wx.RIGHT, 4)
		self.lblStatus = wx.StaticText(p, label=_("Cargando datos..."))
		sizer_loc.Add(self.lblStatus, 0, wx.LEFT|wx.TOP|wx.BOTTOM, 4)
		main.Add(sizer_loc, 0, wx.EXPAND|wx.ALL, 8)

		# ── datos actuales ────────────────────────────────────────────────────
		prefs  = self._cfg.get("prefs", dict(PREFS_DEFECTO))
		box_c  = wx.StaticBox(p, label=_("Datos actuales que quiero escuchar"))
		sizer_c = wx.StaticBoxSizer(box_c, wx.VERTICAL)
		for key, label, _descartado, tipo in OPCIONES:
			if tipo in ("current", "special", "special_current", "air_quality"):
				cb = wx.CheckBox(p, label=_(label))
				cb.SetValue(prefs.get(key, True))
				self._checks[key] = cb
				sizer_c.Add(cb, 0, wx.LEFT|wx.TOP, 3)
		main.Add(sizer_c, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 8)

		# ── datos del día ─────────────────────────────────────────────────────
		box_d  = wx.StaticBox(p, label=_("Datos del día que quiero escuchar"))
		sizer_d = wx.StaticBoxSizer(box_d, wx.VERTICAL)
		for key, label, _descartado, tipo in OPCIONES:
			if tipo in ("daily", "special_daily"):
				cb = wx.CheckBox(p, label=_(label))
				cb.SetValue(prefs.get(key, True))
				self._checks[key] = cb
				sizer_d.Add(cb, 0, wx.LEFT|wx.TOP, 3)
		main.Add(sizer_d, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 8)

		# ── pronóstico ────────────────────────────────────────────────────────
		box_f  = wx.StaticBox(p, label=_("Pronóstico extendido (NVDA+Shift+W)"))
		sizer_f = wx.StaticBoxSizer(box_f, wx.HORIZONTAL)
		sizer_f.Add(wx.StaticText(p, label=_("&Días a consultar (1 a 16):")), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 4)
		try:
			init_days = max(1, min(16, int(self._cfg.get("forecast_days", 6))))
		except (ValueError, TypeError, OverflowError):
			init_days = 6
		self.spinDays = wx.SpinCtrl(p, min=1, max=16, initial=init_days)
		sizer_f.Add(self.spinDays, 0, wx.LEFT|wx.RIGHT, 8)
		main.Add(sizer_f, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 8)

		# ── alertas oficiales en reportes ───────────────────────────────────
		try:
			init_alertas = bool(self._cfg.get("incluir_alertas_en_reporte", True))
		except Exception:
			init_alertas = True
		self.chkAlertas = wx.CheckBox(p, label=_("Incluir alertas oficiales en los reportes de clima y pronóstico"))
		self.chkAlertas.SetValue(init_alertas)
		main.Add(self.chkAlertas, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 8)

		# Red y reintentos
		box_red = wx.StaticBox(p, label=_("Red y reintentos"))
		sizer_red = wx.StaticBoxSizer(box_red, wx.VERTICAL)
		sizer_red.Add(wx.StaticText(p, label=_("Número máximo de reintentos (0 para desactivar):")), 0, wx.LEFT|wx.TOP, 4)
		try:
			retries = max(0, min(10, int(self._cfg.get("network_retries", PREFS_DEFECTO["network_retries"]))))
		except (ValueError, TypeError, OverflowError):
			retries = PREFS_DEFECTO["network_retries"]
		self.spinRetries = wx.SpinCtrl(p, min=0, max=10, initial=retries)
		sizer_red.Add(self.spinRetries, 0, wx.LEFT|wx.RIGHT, 4)
		sizer_red.Add(wx.StaticText(p, label=_("Segundos de espera entre reintentos:")), 0, wx.LEFT|wx.TOP, 4)
		try:
			retry_delay = max(1, min(60, int(self._cfg.get("network_retry_delay", PREFS_DEFECTO["network_retry_delay"]))))
		except (ValueError, TypeError, OverflowError):
			retry_delay = int(PREFS_DEFECTO["network_retry_delay"])
		self.spinRetryDelay = wx.SpinCtrl(p, min=1, max=60, initial=retry_delay)
		sizer_red.Add(self.spinRetryDelay, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 4)
		main.Add(sizer_red, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 8)

		# ── botones ───────────────────────────────────────────────────────────
		row = wx.BoxSizer(wx.HORIZONTAL)
		self.btnSave = wx.Button(p, wx.ID_OK, label=_("&Guardar todo"))
		self.btnSave.Disable()
		self.btnSave.Bind(wx.EVT_BUTTON, self.onSave)
		row.Add(self.btnSave, 0, wx.RIGHT, 8)
		self.btnCancel = wx.Button(p, wx.ID_CANCEL, label=_("&Cancelar"))
		self.btnCancel.Bind(wx.EVT_BUTTON, self.onCancel)
		row.Add(self.btnCancel)
		main.Add(row, 0, wx.ALL, 10)

		self.SetAffirmativeId(wx.ID_OK)
		self.SetEscapeId(wx.ID_CANCEL)

		p.SetSizer(main)
		p.Layout()
		self.SetSize((480, 700))
		self.SetMinSize((440, 400))

		self._progressTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self._onProgressTick, self._progressTimer)
		self.Bind(wx.EVT_CLOSE, self._onClose)
		self._progressTimer.Start(80)

	def _safeDestroy(self):
		"""Destruye el diálogo una sola vez, evitando doble Destroy."""
		if getattr(self, "_destroyed", False):
			return
		self._destroyed = True
		try:
			self.Destroy()
		except Exception as e:
			if _esObjetoDestruido(e):
				return
			log.debugWarning("ClimaAccesible: Destroy fallo: {}".format(e), exc_info=True)

	def _onClose(self, event):
		"""Garantiza que el timer se detenga siempre al cerrar el diálogo."""
		self._isClosing = True
		self._stopProgress()
		if hasattr(self, "IsModal") and self.IsModal():
			self.EndModal(wx.ID_CANCEL)
		else:
			self._safeDestroy()

	def onCancel(self, event):
		"""Manejador del botón Cancelar para descartar cambios y detener procesos en curso."""
		self._isClosing = True
		self._stopProgress()
		if hasattr(self, "IsModal") and self.IsModal():
			self.EndModal(wx.ID_CANCEL)
		else:
			self._safeDestroy()

	def _onProgressTick(self, event):
		"""Actualiza el indicador visual de progreso mientras se cargan los datos geográficos."""
		try:
			if not self or getattr(self, "_isClosing", False):
				return
		except Exception as e:
			if _esObjetoDestruido(e):
				return
			log.debugWarning("ClimaAccesible: _onProgressTick ignora objeto destruido: {}".format(e), exc_info=True)
			return
		try:
			if hasattr(self, "progressBar") and self.progressBar:
				self.progressBar.SetValue((self.progressBar.GetValue() + 3) % 101)
		except Exception as e:
			if _esObjetoDestruido(e):
				return
			log.debugWarning("ClimaAccesible: _onProgressTick fallo: {}".format(e), exc_info=True)

	def _stopProgress(self):
		"""Detiene el temporizador de carga y oculta la barra de progreso."""
		try:
			if not self:
				return
		except Exception as e:
			if _esObjetoDestruido(e):
				return
			log.debugWarning("ClimaAccesible: _stopProgress objeto destruido: {}".format(e), exc_info=True)
			return
		try:
			if hasattr(self, "_progressTimer") and self._progressTimer and self._progressTimer.IsRunning():
				self._progressTimer.Stop()
		except Exception as e:
			if _esObjetoDestruido(e):
				return
			log.debugWarning("ClimaAccesible: _stopProgress timer fallo: {}".format(e), exc_info=True)
		try:
			if hasattr(self, "progressBar") and self.progressBar:
				self.progressBar.Hide()
		except Exception as e:
			if _esObjetoDestruido(e):
				return
			log.debugWarning("ClimaAccesible: _stopProgress gauge fallo: {}".format(e), exc_info=True)

	# ── eventos de cambio automático ──────────────────────────────────────────

	def onCountryChange(self, event):
		"""Actualiza la lista de regiones al cambiar la selección del combo de países."""
		idx = self.cboCountry.GetSelection()
		if idx != wx.NOT_FOUND:
			self._do_fill_regions(idx, select_first=True)

	def onRegionChange(self, event):
		"""Actualiza la lista de ciudades al cambiar la selección del combo de regiones."""
		idx = self.cboRegion.GetSelection()
		if idx != wx.NOT_FOUND:
			self._do_fill_cities(idx, select_first=True)

	def onCityChange(self, event):
		"""Habilita el botón de guardar una vez seleccionada una ciudad válida."""
		if self.cboCity.GetSelection() != wx.NOT_FOUND:
			self.btnSave.Enable()

	# ── países ────────────────────────────────────────────────────────────────

	def _load_countries(self):
		"""Carga en un hilo secundario la base de datos geográfica para no congelar la interfaz."""
		try:
			data      = getGeoData()
			countries = [(c[0], c[1]) for c in data if isinstance(c, (list, tuple)) and len(c) >= 2 and c[0]]
			if not self._isClosing:
				wx.CallAfter(self._populate_countries, countries)
		except Exception as e:
			if _esObjetoDestruido(e):
				return
			log.error("ClimaAccesible: error al cargar países: {}".format(e))
			if not getattr(self, "_isClosing", False):
				try:
					wx.CallAfter(self._stopProgress)
					wx.CallAfter(self._status, _("Error al cargar datos geográficos."))
				except Exception as _ce:
					log.debugWarning("ClimaAccesible: CallAfter fallo: {}".format(_ce), exc_info=True)

	def _populate_countries(self, countries):
		"""Rellena la lista de países cuando termina de cargarse el archivo de lugares.

		Deja elegido el país que se guardó la última vez; si no había ninguno,
		Uruguay; y si tampoco está, el primero de la lista. Elegido el país, pide
		las regiones de ese país. Si la ventana se cerró mientras se cargaba, no
		hace nada, para no escribir en una ventana que ya no existe.
		"""
		try:
			if not self or getattr(self, "_isClosing", False):
				return
		except Exception as e:
			if _esObjetoDestruido(e):
				return
			log.debugWarning("ClimaAccesible: _populate_countries objeto destruido: {}".format(e), exc_info=True)
			return
		try:
			self._stopProgress()
			self._countries = countries
			self.cboCountry.Clear()
			self.cboCountry.AppendItems([name for name, _ in self._countries])
			self.cboCountry.Enable()

			codes = [c[1] for c in self._countries]
			saved = self._cfg.get("country_iso2", "")
			if saved in codes:
				idx = codes.index(saved)
				self.cboCountry.SetSelection(idx)
				self._do_fill_regions(idx, select_first=False)
			elif "UY" in codes:
				idx = codes.index("UY")
				self.cboCountry.SetSelection(idx)
				self._do_fill_regions(idx, select_first=True)
			elif len(self._countries) > 0:
				self.cboCountry.SetSelection(0)
				self._do_fill_regions(0, select_first=True)

			focused = self.FindFocus() if hasattr(self, "FindFocus") else None
			if focused in (getattr(self, "btnCancel", None), self, None):
				try:
					if self.cboCountry.IsEnabled():
						self.cboCountry.SetFocus()
				except Exception:
					pass
			if self.cboCity.GetSelection() != wx.NOT_FOUND:
				self.btnSave.Enable()
			self._status(_("Listo. Elige tu ubicación."))
		except Exception as e:
			log.debugWarning("ClimaAccesible: _populate_countries ignorado: {}".format(e))

	# ── regiones ──────────────────────────────────────────────────────────────

	def _do_fill_regions(self, country_idx, select_first=False):
		"""Rellena la lista de regiones del país elegido y encadena con las ciudades.

		Con select_first en False intenta dejar puesta la región guardada; con
		True se queda con la primera. Si el país no tiene regiones, apaga las
		listas de región y ciudad y el botón Guardar, para que no se pueda
		guardar una ubicación a medias.
		"""
		try:
			if not self or getattr(self, "_isClosing", False):
				return
		except Exception as e:
			if _esObjetoDestruido(e):
				return
			log.debugWarning("ClimaAccesible: _do_fill_regions objeto destruido: {}".format(e), exc_info=True)
			return
		try:
			data    = getGeoData()
			if country_idx < 0 or country_idx >= len(data):
				return
			country = data[country_idx]
			raw_states = country[2] if isinstance(country, (list, tuple)) and len(country) > 2 and isinstance(country[2], list) else []
			valid_states = [s for s in raw_states if isinstance(s, (list, tuple))]
			states  = sorted(valid_states, key=lambda s: _normTxt(s[0]) if len(s) > 0 else "")
			self._regions = [(s[0], s[2]) for s in states if len(s) >= 3 and s[0]]
			self.cboRegion.Clear()
			if self._regions:
				self.cboRegion.AppendItems([name for name, _ in self._regions])
				self.cboRegion.Enable()

				saved_region = self._cfg.get("region_name", "")
				names = [r[0] for r in self._regions]
				if not select_first and saved_region in names:
					idx = names.index(saved_region)
					self.cboRegion.SetSelection(idx)
					self._do_fill_cities(idx, select_first=False)
				else:
					self.cboRegion.SetSelection(0)
					self._do_fill_cities(0, select_first=True)
			else:
				self.cboRegion.Disable()
				self.cboCity.Clear()
				self.cboCity.Disable()
				self.btnSave.Disable()
				self._status(_("Este país no tiene regiones disponibles."))
				try:
					if hasattr(self, "cboCountry") and self.cboCountry and self.cboCountry.IsEnabled():
						self.cboCountry.SetFocus()
				except Exception:
					pass
		except Exception as e:
			log.debugWarning("ClimaAccesible: _do_fill_regions error: {}".format(e))

	# ── ciudades ──────────────────────────────────────────────────────────────

	def _do_fill_cities(self, region_idx, select_first=False):
		"""Rellena la lista de ciudades de la región elegida.

		Es el último eslabón de las tres listas. Con select_first en False intenta
		dejar puesta la ciudad guardada, validando nombre + coordenadas para no
		confundir homónimas (H1: p. ej. Huangshan x2 en Anhui, que se muestran
		como "Nombre — lat,lon"). En cuanto hay al menos una ciudad se enciende
		el botón Guardar; si no hay ninguna, se apaga, se avisa y el foco no
		queda en el combo deshabilitado (H3). Si hay más de 2000, se muestran
		2000 y se anuncia el total (H4).
		"""
		try:
			if not self or getattr(self, "_isClosing", False):
				return
		except Exception as e:
			if _esObjetoDestruido(e):
				return
			log.debugWarning("ClimaAccesible: _do_fill_cities objeto destruido: {}".format(e), exc_info=True)
			return
		try:
			if region_idx < 0 or region_idx >= len(self._regions):
				return
			_entryRegion = self._regions[region_idx]
			raw_cities = _entryRegion[1] if isinstance(_entryRegion, (list, tuple)) and len(_entryRegion) > 1 else []
			raw_cities_list = raw_cities if isinstance(raw_cities, (list, tuple)) else []
			self._cities = sorted(
				[(c[0], c[1], c[2]) for c in raw_cities_list if isinstance(c, (list, tuple)) and len(c) >= 3 and c[0]],
				key=lambda x: _normTxt(str(x[0]))
			)
			total = len(self._cities)
			if total > 2000:
				log.warning("ClimaAccesible: región con {} ciudades, aplicando filtro (se muestran 2000).".format(total))
				# ComboBox filtrado: limitar a 2000 para no congelar wx con 156k ciudades.
				self._cities = self._cities[:2000]
			self.cboCity.Clear()
			if self._cities:
				_conteo = {}
				for _nm, _la, _lo in self._cities:
					_kc = _normTxt(str(_nm))
					_conteo[_kc] = _conteo.get(_kc, 0) + 1
				_etiquetas = []
				for _nm, _la, _lo in self._cities:
					if _conteo.get(_normTxt(str(_nm)), 0) > 1:
						_etiquetas.append("{} \u2014 {},{}".format(_nm, _la, _lo))
					else:
						_etiquetas.append(str(_nm))
				self.cboCity.AppendItems(_etiquetas)
				self.cboCity.Enable()
				self.btnSave.Enable()

				saved_city = self._cfg.get("city", "")
				saved_lat = self._cfg.get("lat")
				saved_lon = self._cfg.get("lon")
				elegido = -1
				if not select_first and saved_city:
					try:
						_slat = _safe_float(saved_lat, default=None)
						_slon = _safe_float(saved_lon, default=None)
					except Exception:
						_slat, _slon = None, None
					for _idx, (_nm, _la, _lo) in enumerate(self._cities):
						if str(_nm) != str(saved_city):
							continue
						if _slat is not None and _slon is not None:
							try:
								_cla = _safe_float(_la, default=None)
								_clo = _safe_float(_lo, default=None)
							except Exception:
								_cla, _clo = None, None
							if _cla is None or _clo is None:
								continue
							_ok = (_cla == _slat and _clo == _slon)
							if not _ok:
								try:
									_ok = (round(_cla, 4) == round(_slat, 4) and round(_clo, 4) == round(_slon, 4))
								except Exception:
									_ok = False
							if not _ok:
								continue
						elegido = _idx
						break
					if elegido < 0:
						names = [c[0] for c in self._cities]
						if saved_city in names:
							elegido = names.index(saved_city)
				if elegido >= 0:
					self.cboCity.SetSelection(elegido)
				else:
					self.cboCity.SetSelection(0)
				if total > 2000:
					self._status(_("Mostrando 2000 de {} ciudades. Elige otra región o filtra por país y región.").format(total))
			else:
				self.cboCity.Disable()
				self.btnSave.Disable()
				self._status(_("Esta región no tiene ciudades disponibles."))
				try:
					if hasattr(self, "cboRegion") and self.cboRegion and self.cboRegion.IsEnabled():
						self.cboRegion.SetFocus()
				except Exception:
					pass
		except Exception as e:
			log.debugWarning("ClimaAccesible: _do_fill_cities error: {}".format(e))

	# ── guardar ───────────────────────────────────────────────────────────────

	def onSave(self, event):
		"""Botón Guardar: escribe la configuración en el disco y cierra la ventana.

		Comprueba que haya una ciudad elegida. Guarda la ciudad con sus
		coordenadas, la región, el país, qué datos quieres oír y cuántos días de
		pronóstico. Después lo confirma en pantalla y recuerda que el atajo para
		consultar el clima es NVDA+W.
		"""
		ci = self.cboCity.GetSelection()
		ri = self.cboRegion.GetSelection()
		co = self.cboCountry.GetSelection()
		if (ci == wx.NOT_FOUND or ri == wx.NOT_FOUND or co == wx.NOT_FOUND
				or ci >= len(self._cities) or ri >= len(self._regions) or co >= len(self._countries)
				or not self._cities or not self._regions or not self._countries):
			self._status(_("Elige un país, región y ciudad antes de guardar."))
			return
		name, lat, lon   = self._cities[ci]
		region_name, _descartado_region  = self._regions[ri]
		_descartado_pais, country_iso2  = self._countries[co]
		prefs = {key: cb.GetValue() for key, cb in self._checks.items()}
		try:
			lat_val, lon_val = _coord_valida(lat, lon)
		except ValueError:
			self._status(_("Coordenadas no válidas para {} ({}). Vuelve a elegir país, región y ciudad.").format(name, region_name))
			return
		try:
			dias_val = max(1, min(16, int(self.spinDays.GetValue())))
		except (ValueError, TypeError, OverflowError):
			dias_val = 6
		try:
			net_retries = int(self.spinRetries.GetValue())
			net_delay = float(self.spinRetryDelay.GetValue())
		except Exception as e:
			log.debugWarning("ClimaAccesible: red config inválida: {}".format(e), exc_info=True)
			net_retries = 1
			net_delay = 1.0

		success = saveJSON(_configPath(), {
			"city":          name,
			"lat":           lat_val,
			"lon":           lon_val,
			"region_name":   region_name,
			"country_iso2":  country_iso2,
			"prefs":         prefs,
			"forecast_days": dias_val,
			"network_retries": net_retries,
			"network_retry_delay": net_delay,
			"incluir_alertas_en_reporte": bool(self.chkAlertas.GetValue()),
		})
		if success:
			try:
				_lat_r = round(float(lat_val), 1)
				_lon_r = round(float(lon_val), 1)
			except Exception as e:
				log.debugWarning("ClimaAccesible: redondeo coords fallo: {}".format(e), exc_info=True)
				_lat_r, _lon_r = "?", "?"
			log.info("ClimaAccesible: Guardando configuracion - Ciudad: {}, Coordenadas: ({}, {}), Dias: {}".format(str(name)[:80], _lat_r, _lon_r, dias_val))
			self._status(_("Configuración guardada."))
			gui.messageBox(
				_("Configuración guardada.\nCiudad: {c}\nUsa NVDA+W para consultar el clima.").format(c=name),
				_("ClimaAccesible"), wx.OK | wx.ICON_INFORMATION, parent=self
			)
			self._isClosing = True
			self._stopProgress()
			if hasattr(self, "IsModal") and self.IsModal():
				self.EndModal(wx.ID_OK)
			else:
				self._safeDestroy()
		else:
			self._status(_("Error al guardar la configuración."))
			gui.messageBox(
				_("No se pudo guardar la configuración. Revisa los permisos de la carpeta."),
				_("Error"), wx.OK | wx.ICON_ERROR, parent=self
			)

	def _status(self, text):
		"""Actualiza la etiqueta de estado visual y anuncia el mensaje a través de NVDA."""
		try:
			if not self or getattr(self, "_isClosing", False):
				return
		except Exception as e:
			if _esObjetoDestruido(e):
				return
			log.debugWarning("ClimaAccesible: _status objeto destruido: {}".format(e), exc_info=True)
			return
		try:
			if hasattr(self, "lblStatus") and self.lblStatus:
				self.lblStatus.SetLabel(text)
		except Exception as e:
			if _esObjetoDestruido(e):
				return
			log.debugWarning("ClimaAccesible: _status label fallo: {}".format(e), exc_info=True)
		try:
			wx.CallAfter(ui.message, text)
		except Exception as e:
			log.debugWarning("ClimaAccesible: _status CallAfter fallo: {}".format(e), exc_info=True)


# ── plugin principal ──────────────────────────────────────────────────────────

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Plugin global de NVDA para consultar pronósticos meteorológicos accesibles mediante Open-Meteo."""

	scriptCategory = _("ClimaAccesible")

	def __init__(self):
		"""Inicializa el plugin global de clima, registrando el submenú en Herramientas y tareas en segundo plano."""
		if getattr(globalVars.appArgs, "secureMode", False):
			log.warning("ClimaAccesible: NVDA en modo seguro. Se cancela la carga del complemento por seguridad.")
			raise globalPluginHandler.ActionCancelled()
		super(GlobalPlugin, self).__init__()
		self._stopping = threading.Event()
		self._isConfigOpen = False
		self._fetchingWeatherActive = False
		self._fetchingForecastActive = False
		self._fetchingAlertsActive = False
		if getattr(self, "_fetchLock", None) is None or not hasattr(getattr(self, "_fetchLock", None), "acquire"):
			self._fetchLock = threading.Lock()
		self._lastRequest = {}
		self._toolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu
		self._subMenu = wx.Menu()
		self._itemConfig = self._subMenu.Append(wx.Window.NewControlId(), _("Configuración del complemento"))
		self._itemAlerts = self._subMenu.Append(wx.Window.NewControlId(), _("Consultar alertas meteorológicas oficiales"))
		self._itemConflicts = self._subMenu.Append(wx.Window.NewControlId(), _("Comprobar conflictos con otros complementos..."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._onMenuConfig, self._itemConfig)
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._onMenuAlerts, self._itemAlerts)
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._onMenuConflicts, self._itemConflicts)
		self._subMenuItem = self._toolsMenu.AppendSubMenu(
			self._subMenu, "ClimaAccesible", _("Opciones de ClimaAccesible")
		)
		try:
			threading.Thread(target=self._startupBackgroundWorker, daemon=True).start()
		except Exception as e:
			log.debugWarning("ClimaAccesible: no se pudo iniciar worker: {}".format(e), exc_info=True)
			self._fetchingWeatherActive = False
			self._fetchingForecastActive = False
		ver = ""
		try:
			addon = addonHandler.getCodeAddon()
			if addon and getattr(addon, "manifest", None):
				ver = addon.manifest.get("version", "")
		except Exception as e:
			log.debugWarning("ClimaAccesible: no se pudo leer versión: {}".format(e), exc_info=True)
		ver_str = f" (v{ver})" if ver else ""
		log.info(f"ClimaAccesible: Inicializando complemento{ver_str}...")
		log.info("ClimaAccesible: Submenú registrado en Herramientas exitosamente.")

	def terminate(self):
		"""Se llama cuando NVDA cierra, reinicia o desinstala el complemento."""
		self._stopping.set()
		try:
			if hasattr(self, "_itemConfig") and self._itemConfig:
				gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, source=self._itemConfig)
			if hasattr(self, "_itemAlerts") and self._itemAlerts:
				gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, source=self._itemAlerts)
			if hasattr(self, "_itemConflicts") and self._itemConflicts:
				gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, source=self._itemConflicts)
		except Exception as e:
			log.debugWarning("ClimaAccesible: error al desvincular menú en terminate: {}".format(e), exc_info=True)

		try:
			if hasattr(self, "_subMenuItem") and self._subMenuItem:
				try:
					self._toolsMenu.DestroyItem(self._subMenuItem)
				except Exception as _de:
					try:
						self._toolsMenu.Remove(self._subMenuItem)
					except Exception as _re:
						log.debugWarning("ClimaAccesible: no se pudo retirar submenú: {}".format(_re), exc_info=True)
		except Exception as e:
			log.warning("ClimaAccesible: error al retirar submenú en terminate: {}".format(e))

		super(GlobalPlugin, self).terminate()
		log.info("ClimaAccesible: complemento cerrado correctamente.")

	def _onMenuConfig(self, event):
		"""Manejador de evento del menú para abrir el diálogo de configuración."""
		wx.CallAfter(self._openConfigDialog)

	def _onMenuAlerts(self, event):
		"""Inicia desde el menú la consulta manual de alertas oficiales."""
		self.script_getOfficialAlerts(None)


	# ── scripts ───────────────────────────────────────────────────────────────

	@scriptHandler.script(
		description=_("Anuncia el clima actual de la ciudad configurada."),
		gesture="kb:nvda+w",
		speakOnDemand=True,
		category=scriptCategory,
	)
	def script_getWeather(self, gesture):
		"""Consulta y verbaliza las condiciones meteorológicas actuales de la ciudad seleccionada."""
		log.info("ClimaAccesible: Atajo NVDA+W activado (lectura de clima actual).")
		if getattr(self, "_fetchLock", None) is None or not hasattr(getattr(self, "_fetchLock", None), "acquire"):
			try:
				self._fetchLock = threading.Lock()
			except Exception:
				pass
		with self._fetchLock:
			if getattr(self, "_fetchingWeatherActive", False):
				log.info("ClimaAccesible: Consulta de clima en curso, ignorando atajo repetido.")
				return
			self._fetchingWeatherActive = True
		cfg = loadJSON(_configPath())
		if cfg.get("lat") is None or cfg.get("lon") is None:
			with self._fetchLock:
				self._fetchingWeatherActive = False
			log.warning("ClimaAccesible: Intento de consulta de clima sin ciudad configurada.")
			ui.message(_("No hay ciudad configurada. Usa NVDA+Control+W para configurar."))
			return
		try:
			_lat_r = round(float(str(cfg.get("lat")).strip().replace(",", ".")), 1)
			_lon_r = round(float(str(cfg.get("lon")).strip().replace(",", ".")), 1)
		except Exception as e:
			log.debugWarning("ClimaAccesible: redondeo log fallo: {}".format(e), exc_info=True)
			_lat_r, _lon_r = "?", "?"
		log.info("ClimaAccesible: Consultando reporte para ciudad='{}' ({}, {})...".format(str(cfg.get("city"))[:80], _lat_r, _lon_r))
		ui.message(_("Por favor espera, consultando el clima..."))
		try:
			t = threading.Thread(target=self._fetchWeather, args=(cfg,), daemon=True)
			t.start()
		except Exception as e:
			with self._fetchLock:
				self._fetchingWeatherActive = False
			log.debugWarning("ClimaAccesible: no se pudo iniciar hilo clima: {}".format(e), exc_info=True)

	@scriptHandler.script(
		description=_("Anuncia el pronóstico del clima para los próximos días."),
		gesture="kb:nvda+shift+w",
		speakOnDemand=True,
		category=scriptCategory,
	)
	def script_getForecast(self, gesture):
		"""Consulta y verbaliza el pronóstico extendido de varios días para la ciudad seleccionada."""
		log.info("ClimaAccesible: Atajo NVDA+Shift+W activado (lectura de pronóstico extendido).")
		if getattr(self, "_fetchLock", None) is None or not hasattr(getattr(self, "_fetchLock", None), "acquire"):
			try:
				self._fetchLock = threading.Lock()
			except Exception:
				pass
		with self._fetchLock:
			if getattr(self, "_fetchingForecastActive", False):
				log.info("ClimaAccesible: Consulta de pronóstico en curso, ignorando atajo repetido.")
				return
			self._fetchingForecastActive = True
		cfg = loadJSON(_configPath())
		if cfg.get("lat") is None or cfg.get("lon") is None:
			with self._fetchLock:
				self._fetchingForecastActive = False
			log.warning("ClimaAccesible: Intento de consulta de pronóstico sin ciudad configurada.")
			ui.message(_("No hay ciudad configurada. Usa NVDA+Control+W para configurar."))
			return
		dias = cfg.get("forecast_days", 6)
		try:
			dias = max(1, min(16, int(dias)))
		except (ValueError, TypeError, OverflowError):
			dias = 6
		log.info("ClimaAccesible: Consultando pronóstico de {} días para ciudad='{}'...".format(dias, str(cfg.get("city"))[:80]))
		ui.message(_("Por favor espera, consultando el pronóstico de {} días...").format(dias))
		try:
			t = threading.Thread(target=self._fetchForecast, args=(cfg,), daemon=True)
			t.start()
		except Exception as e:
			with self._fetchLock:
				self._fetchingForecastActive = False
			log.debugWarning("ClimaAccesible: no se pudo iniciar hilo pronóstico: {}".format(e), exc_info=True)

	@scriptHandler.script(
		description=_("Abre la ventana de configuración de ClimaAccesible."),
		gesture="kb:nvda+control+w",
		category=scriptCategory,
	)
	def script_openConfig(self, gesture):
		"""Abre el diálogo accesible para ajustar la ciudad y las opciones meteorológicas."""
		wx.CallAfter(self._openConfigDialog)

	@scriptHandler.script(
		description=_("Consulta las alertas meteorológicas oficiales disponibles para la ciudad configurada."),
		category=scriptCategory,
		speakOnDemand=True,
	)
	def script_getOfficialAlerts(self, gesture):
		"""Consulta bajo demanda: nunca anuncia alertas automáticamente ni las infiere."""
		log.info("ClimaAccesible: Consulta manual de alertas oficiales iniciada.")
		if getattr(self, "_fetchLock", None) is None or not hasattr(getattr(self, "_fetchLock", None), "acquire"):
			self._fetchLock = threading.Lock()
		with self._fetchLock:
			if self._fetchingAlertsActive:
				marcada = getattr(self, "_fetchingAlertsStarted", 0.0)
				try:
					atascada = (time.monotonic() - float(marcada)) > 90.0
				except Exception:
					atascada = False
				if not atascada:
					self._safeMessage(_("La consulta de alertas oficiales ya está en curso."))
					return
				log.warning("ClimaAccesible: marca de alertas atascada más de 90s, se libera y se reintenta.")
			self._fetchingAlertsActive = True
			try:
				self._fetchingAlertsStarted = time.monotonic()
			except Exception:
				pass
		cfg = loadJSON(_configPath())
		if cfg.get("lat") is None or cfg.get("lon") is None or not cfg.get("country_iso2"):
			with self._fetchLock:
				self._fetchingAlertsActive = False
			self._safeMessage(_("No hay una ciudad configurada. Configúrala antes de consultar alertas."))
			return
		self._safeMessage(_("Consultando alertas meteorológicas oficiales, esto puede tardar unos segundos..."))
		try:
			threading.Thread(target=self._fetchOfficialAlerts, args=(cfg,), daemon=True).start()
		except Exception as e:
			with self._fetchLock:
				self._fetchingAlertsActive = False
			log.debugWarning("ClimaAccesible: no se pudo iniciar consulta de alertas: {}".format(e), exc_info=True)
			self._safeMessage(_("No se pudo iniciar la consulta de alertas oficiales."))

	def _openConfigDialog(self):
		"""Abre la ventana accesible de configuración garantizando una única instancia activa."""
		if getattr(self, "_fetchLock", None) is None or not hasattr(getattr(self, "_fetchLock", None), "acquire"):
			try:
				self._fetchLock = threading.Lock()
			except Exception:
				pass
		with self._fetchLock:
			if getattr(self, "_isConfigOpen", False):
				log.info("ClimaAccesible: Diálogo de configuración ya abierto, omitiendo.")
				return
			self._isConfigOpen = True
		log.info("ClimaAccesible: Abriendo diálogo accesible de configuración...")
		gui.mainFrame.prePopup()
		dlg = None
		try:
			dlg = ConfigDialog(gui.mainFrame)
			dlg.ShowModal()
		except Exception as e:
			log.error(f"ClimaAccesible: error en diálogo de configuración: {e}", exc_info=True)
		finally:
			if dlg:
				try:
					if not getattr(dlg, "_destroyed", False):
						dlg.Destroy()
				except Exception as e:
					if not _esObjetoDestruido(e):
						log.debugWarning("ClimaAccesible: Destroy diálogo fallo: {}".format(e), exc_info=True)
			try:
				gui.mainFrame.postPopup()
			except Exception as e:
				log.debugWarning("ClimaAccesible: postPopup fallo: {}".format(e), exc_info=True)
			try:
				with self._fetchLock:
					self._isConfigOpen = False
			except AttributeError:
				self._isConfigOpen = False
			log.info("ClimaAccesible: Diálogo de configuración cerrado.")

	# ── helper interno: anunciar solo si NVDA sigue activo ────────────────────

	def _safeMessage(self, text):
		"""Llama a ui.message de forma segura solo si NVDA no está cerrándose."""
		try:
			if getattr(self, "_stopping", None) is not None and self._stopping.is_set():
				return
		except Exception as e:
			log.debugWarning("ClimaAccesible: _safeMessage stopping check fallo: {}".format(e), exc_info=True)
			return
		try:
			short = str(text)[:200]
		except Exception as e:
			log.debugWarning("ClimaAccesible: truncado mensaje fallo: {}".format(e), exc_info=True)
			short = "?"
		log.info("ClimaAccesible: Anunciando al usuario: '{}'".format(short))
		try:
			wx.CallAfter(ui.message, text)
		except Exception as e:
			log.debugWarning("ClimaAccesible: _safeMessage CallAfter fallo: {}".format(e), exc_info=True)
			try:
				core.callLater(0, ui.message, text)
			except Exception as ex:
				log.error("ClimaAccesible: _safeMessage falló: {}".format(ex), exc_info=True)

	def _getUserAgent(self):
		"""Construye la cabecera User-Agent con la versión activa del complemento para la API."""
		try:
			addon = addonHandler.getCodeAddon()
			if addon and getattr(addon, "manifest", None):
				return f"ClimaAccesible/{addon.manifest.get('version', '1.9.8')}"
		except Exception as e:
			log.debugWarning("ClimaAccesible: UserAgent fallback: {}".format(e), exc_info=True)
		return "ClimaAccesible/1.9.8"

	def _manejarErrorPeticion(self, error, operacion="el clima"):
		"""Gestiona y verbaliza de forma unificada y segura los fallos de red o de la API meteorológica."""
		if self._stopping.is_set():
			return
		if isinstance(error, (TimeoutError, socket.timeout)):
			log.error(f"ClimaAccesible: Tiempo de espera agotado en {operacion}.", exc_info=True)
			self._safeMessage(_("Tiempo de espera agotado al consultar {}. Comprueba tu conexión o inténtalo nuevamente.").format(operacion))
		elif isinstance(error, urllib.error.HTTPError):
			motivo = "sin detalle"
			try:
				raw = error.read(8192) if hasattr(error, "read") else b""
				if isinstance(raw, bytes):
					txt = raw.decode("utf-8", errors="replace")
				else:
					txt = str(raw)[:500]
				parsed = json.loads(txt) if txt.strip() else {}
				if isinstance(parsed, dict):
					motivo = str(parsed.get("reason", "sin detalle"))[:200]
			except Exception as e:
				log.debugWarning("ClimaAccesible: no se pudo extraer motivo HTTP: {}".format(e), exc_info=True)
				motivo = "sin detalle"
			try:
				_code = int(getattr(error, "code", 0))
			except Exception as e:
				log.debugWarning("ClimaAccesible: código HTTP ilegible: {}".format(e), exc_info=True)
				_code = 0
			log.error("ClimaAccesible: Error HTTP {} en {}: {}".format(_code, operacion, motivo[:200]), exc_info=True)
			self._safeMessage(_("Error del servidor: código {}. Motivo: {}").format(_code, motivo))
		elif isinstance(error, urllib.error.URLError):
			try:
				_reason = str(getattr(error, "reason", error))[:200]
			except Exception as e:
				log.debugWarning("ClimaAccesible: reason ilegible: {}".format(e), exc_info=True)
				_reason = "?"
			log.error("ClimaAccesible: Error de conexión de red (URLError) en {}: {}".format(operacion, _reason), exc_info=True)
			self._safeMessage(_("No se pudo conectar al servidor. Verifica tu conexión a Internet."))
		elif isinstance(error, (json.JSONDecodeError, UnicodeDecodeError)):
			log.error(f"ClimaAccesible: Respuesta no válida recibida en {operacion} (posible portal cautivo, codificación errónea o HTML).", exc_info=True)
			self._safeMessage(_("Respuesta no válida del servidor meteorológico. Comprueba tu conexión a Internet."))
		else:
			try:
				_err_txt = str(error)[:200]
			except Exception as e:
				log.debugWarning("ClimaAccesible: error ilegible: {}".format(e), exc_info=True)
				_err_txt = "?"
			log.error("ClimaAccesible: Error inesperado en {}: {}".format(operacion, _err_txt), exc_info=True)
			self._safeMessage(_("Error inesperado al consultar {}.").format(operacion))

	def _getJsonFromApi(self, url, label="general"):
		"""Envía una petición JSON con reintento automático y decodifica su respuesta."""
		try:
			_url_log = str(url)[:200]
		except Exception as e:
			log.debugWarning("ClimaAccesible: url log fallo: {}".format(e), exc_info=True)
			_url_log = "?"
		log.info("ClimaAccesible: Enviando petición HTTP ({}): {}".format(label, _url_log))
		# Caché 5min + debounce 2s por URL.
		try:
			_now = time.monotonic()
			with _apiCacheLock:
				_hit = _API_CACHE.get(url)
				if _hit is not None:
					_ts, _data = _hit
					_age = _now - _ts
					if _age < _API_CACHE_TTL:
						if _age < _API_DEBOUNCE:
							log.debugWarning("ClimaAccesible: debounce {:.2f}s para {}".format(_age, label))
						return _data
					else:
						try:
							del _API_CACHE[url]
						except KeyError:
							pass
		except Exception as e:
			log.debugWarning("ClimaAccesible: caché lectura fallo: {}".format(e), exc_info=True)
		req = urllib.request.Request(url, headers={"User-Agent": self._getUserAgent()})
		raw_bytes = None
		cfg = loadJSON(_configPath())
		try:
			max_retries = int(cfg.get("network_retries", PREFS_DEFECTO["network_retries"]))
		except (ValueError, TypeError, OverflowError):
			max_retries = 1
		max_retries = max(0, min(3, max_retries))
		try:
			retry_delay = float(cfg.get("network_retry_delay", PREFS_DEFECTO["network_retry_delay"]))
		except (ValueError, TypeError, OverflowError):
			retry_delay = 1.0
		retry_delay = max(0.5, min(5.0, retry_delay))
		t_end = time.monotonic() + 25
		for attempt in range(max_retries + 1):
			if self._stopping.is_set():
				return None
			restante = t_end - time.monotonic()
			if restante <= 0:
				raise TimeoutError(_("Tiempo de espera agotado al consultar {}").format(label))
			timeout = max(1.0, min(10.0, restante))
			try:
				t0 = time.time()
				with urllib.request.urlopen(req, timeout=timeout) as r:
					raw_bytes = r.read(65536)
					elapsed = time.time() - t0
					status_code = getattr(r, 'status', 200)
					log.info("ClimaAccesible: Respuesta ({}) recibida en {:.2f}s (HTTP {}, {} bytes, intento {}).".format(label, elapsed, status_code, len(raw_bytes), attempt + 1))
					break
			except urllib.error.HTTPError as http_err:
				# Si el servidor responde con 5xx (error temporal) o 429 (rate limit), vale la pena reintentar.
				# Si es 4xx (como 400 Bad Request), reintentar no sirve, abortamos de inmediato.
				if (http_err.code >= 500 or http_err.code == 429) and attempt < max_retries and not self._stopping.is_set():
					restante2 = t_end - time.monotonic()
					if restante2 <= 0:
						raise
					log.warning(f"ClimaAccesible: Reintentando petición ({label}) tras error HTTP {http_err.code}")
					if self._stopping.wait(timeout=min(retry_delay, max(0.1, restante2))):
						break
					continue
				raise
			except (TimeoutError, socket.timeout, urllib.error.URLError) as net_err:
				if attempt < max_retries and not self._stopping.is_set():
					restante2 = t_end - time.monotonic()
					if restante2 <= 0:
						raise
					log.warning("ClimaAccesible: Reintentando petición ({}) tras error de red: {}".format(label, str(net_err)[:200]))
					if self._stopping.wait(timeout=min(retry_delay, max(0.1, restante2))):
						break
					continue
				raise

		if self._stopping.is_set():
			return None
		if not raw_bytes:
			return None
		data = json.loads(raw_bytes.decode("utf-8-sig"))
		try:
			with _apiCacheLock:
				_API_CACHE[url] = (time.monotonic(), data)
		except Exception as e:
			log.debugWarning("ClimaAccesible: caché escritura fallo: {}".format(e), exc_info=True)
		return data

	def _fetchOfficialAlerts(self, cfg):
		"""Consulta un proveedor oficial conocido y anuncia un resumen seguro.

		La arquitectura se selecciona por ISO de país. Los países sin proveedor no
		se estiman con datos de pronóstico: se informa la falta de cobertura oficial.
		"""
		try:
			iso = str(cfg.get("country_iso2") or "").upper().strip()
			provider = ALERTAS_PROVEEDORES.get(iso)
			if not provider:
				self._safeMessage(_("No hay una fuente oficial de alertas configurada todavía para este país. El complemento no inventará alertas a partir del pronóstico."))
				return
			lat, lon = _coord_valida(cfg.get("lat"), cfg.get("lon"))
			url = provider["url"].format(lat=lat, lon=lon)
			data = self._getJsonFromApi(url, "alertas oficiales de " + provider["nombre"])
			if self._stopping.is_set():
				return
			if data is None:
				self._safeMessage(_("No se recibieron alertas oficiales. Inténtalo nuevamente."))
				return
			if provider["tipo"] == "nws_json":
				alertas = _alertasNWS(data)
			elif provider["tipo"] == "uruguay_json":
				alertas = _alertasUruguay(data)
			else:
				alertas = []
			self._safeMessage(_resumenAlertas(alertas, provider["nombre"]))
		except Exception as e:
			log.debugWarning("ClimaAccesible: consulta de alertas oficiales falló: {}".format(str(e)[:200]), exc_info=True)
			self._manejarErrorPeticion(e, _("las alertas meteorológicas oficiales"))
		finally:
			try:
				with self._fetchLock:
					self._fetchingAlertsActive = False
			except Exception:
				self._fetchingAlertsActive = False

	def _anexoAlertas(self, cfg):
		"""Devuelve ' resumen' para pegar al final de un reporte, o ''.

		Nunca lanza: cualquier fallo o falta de cobertura devuelve silencio para
		no romper el reporte del clima ni repetir avisos en cada consulta. Solo
		habla cuando hay al menos una alerta oficial vigente.
		"""
		try:
			if not cfg.get("incluir_alertas_en_reporte", True):
				return ""
			iso = str(cfg.get("country_iso2") or "").upper().strip()
			provider = ALERTAS_PROVEEDORES.get(iso)
			if not provider:
				return ""
			lat, lon = _coord_valida(cfg.get("lat"), cfg.get("lon"))
			url = provider["url"].format(lat=lat, lon=lon)
			data = self._getJsonFromApi(url, "alertas oficiales de " + provider["nombre"])
			if not data:
				return ""
			if provider["tipo"] == "nws_json":
				alertas = _alertasNWS(data)
			elif provider["tipo"] == "uruguay_json":
				alertas = _alertasUruguay(data)
			else:
				return ""
			if not alertas:
				return ""
			return " " + _resumenAlertas(alertas, provider["nombre"])
		except Exception as e:
			log.debugWarning("ClimaAccesible: anexo de alertas omitido: {}".format(str(e)[:200]), exc_info=True)
			return ""

	# ── consulta clima actual ─────────────────────────────────────────────────

	def _fetchWeather(self, cfg):
		"""Consulta el clima de ahora mismo y lo dice en voz alta.

		Se ejecuta en segundo plano, no en el hilo de NVDA. Arma la dirección de
		internet según lo que tengas marcado en la configuración, pide los datos,
		y con ellos construye dos partes: cómo está el tiempo en este momento y el
		resumen del día de hoy. Si algo falla (sin internet, servidor caído, tarda
		demasiado) lo dice con un mensaje que explica qué pasó, en lugar de
		quedarse callado.
		"""
		if getattr(self, "_fetchLock", None) is None or not hasattr(getattr(self, "_fetchLock", None), "acquire"):
			try:
				self._fetchLock = threading.Lock()
			except Exception:
				pass
		try:
			city      = cfg.get("city") or _("tu ciudad")
			lat       = cfg.get("lat")
			lon       = cfg.get("lon")
			prefs_raw = cfg.get("prefs", {})
			claves_validas = {op[0] for op in OPCIONES}
			prefs = {k: prefs_raw.get(k, True) for k in claves_validas}

			url = self._urlDelClimaActual(lat, lon, prefs)
			aq_url = self._urlCalidadAire(lat, lon, prefs)
			
			data = None
			aq_resp = None
			alertas_anexo = ""
			
			error_ocurrido = None
			def fetch_main():
				nonlocal data, error_ocurrido
				try:
					data = self._getJsonFromApi(url, "clima actual")
				except Exception as e:
					error_ocurrido = e
				
			def fetch_aq():
				nonlocal aq_resp
				if aq_url:
					try:
						aq_resp = self._getJsonFromApi(aq_url, "calidad del aire")
					except Exception as e:
						log.debugWarning("ClimaAccesible: calidad aire ignorada: {}".format(str(e)[:200]), exc_info=True)

			def fetch_alertas():
				nonlocal alertas_anexo
				try:
					alertas_anexo = self._anexoAlertas(cfg) or ""
				except Exception as e:
					log.debugWarning("ClimaAccesible: alertas en reporte ignoradas: {}".format(str(e)[:200]), exc_info=True)
					
			t1 = threading.Thread(target=fetch_main, daemon=True)
			t2 = threading.Thread(target=fetch_aq, daemon=True)
			t3 = threading.Thread(target=fetch_alertas, daemon=True)
			t1.start()
			t2.start()
			t3.start()
			t_end = time.monotonic() + 25
			rest = max(0.1, t_end - time.monotonic())
			t1.join(timeout=min(10.0, rest))
			if self._stopping.is_set():
				with self._fetchLock:
					self._fetchingWeatherActive = False
				return
			rest = max(0.1, t_end - time.monotonic())
			t2.join(timeout=min(10.0, rest))

			if t1.is_alive() or t2.is_alive():
				error_ocurrido = TimeoutError(_("Tiempo de espera agotado al consultar el clima"))

			rest = max(0.1, t_end - time.monotonic())
			t3.join(timeout=min(5.0, rest))

			if error_ocurrido:
				raise error_ocurrido

			if self._stopping.is_set():
				return
			if not data:
				self._safeMessage(_("No se recibieron datos. Comprueba tu conexión a Internet."))
				return

			aq_data = {}
			if aq_resp and isinstance(aq_resp.get("current"), dict):
				aq_data = aq_resp.get("current", {})

			c = data.get("current") if isinstance(data.get("current"), dict) else {}
			c.update(aq_data)
			c["elevation"] = data.get("elevation")
			d = data.get("daily") if isinstance(data.get("daily"), dict) else {}
			h = data.get("hourly") if isinstance(data.get("hourly"), dict) else {}
			horas_time = h.get("time",                      []) if isinstance(h.get("time"), list) else []
			horas_prob = h.get("precipitation_probability", []) if isinstance(h.get("precipitation_probability"), list) else []
			horas_prec = h.get("precipitation",             []) if isinstance(h.get("precipitation"), list) else []

			def dv(key):
				"""Extrae el primer valor de la serie diaria o None si la clave no contiene datos."""
				v = d.get(key)
				if isinstance(v, (list, tuple)):
					return v[0] if len(v) > 0 else None
				return v

			d_time = d.get("time", [])
			if d_time and isinstance(d_time, (list, tuple)) and len(d_time) > 0 and d_time[0]:
				fecha_ciudad = str(d_time[0])
			elif "time" in c and "T" in str(c["time"]):
				fecha_ciudad = str(c["time"]).split("T")[0]
			else:
				fecha_ciudad = datetime.date.today().isoformat()

			# Detectar la hora actual de la ciudad para evaluar solo las horas restantes de hoy
			hora_actual = None
			if "time" in c and "T" in str(c["time"]):
				try:
					hora_actual = int(str(c["time"]).split("T")[1].split(":")[0])
				except Exception as e:
					log.debugWarning("ClimaAccesible: hora actual fallback: {}".format(e), exc_info=True)
					hora_actual = datetime.datetime.now().hour
			else:
				hora_actual = datetime.datetime.now().hour

			# Calcular la probabilidad y precipitacion maxima en lo que resta del dia
			probs_rest = []
			precs_rest = []
			if horas_time:
				for idx_h, t in enumerate(horas_time):
					if isinstance(t, str) and t.startswith(fecha_ciudad):
						try:
							h_val = int(t.split("T")[1].split(":")[0])
							if h_val >= hora_actual:
								if idx_h < len(horas_prob) and horas_prob[idx_h] is not None:
									probs_rest.append(int(float(horas_prob[idx_h])))
								if idx_h < len(horas_prec) and horas_prec[idx_h] is not None:
									precs_rest.append(float(horas_prec[idx_h]))
						except Exception as e:
							log.debugWarning("ClimaAccesible: hora diaria ignorada: {}".format(e), exc_info=True)

			prob_max_rest = max(probs_rest) if probs_rest else None
			prec_total_rest = round(sum(precs_rest), 1) if precs_rest else None

			hora_exacta_lluvia = None
			hora_fin_lluvia = None
			rain_blocks = 0
			currently_raining = False
			if prefs.get("hora_lluvia") and horas_time:
				for idx_h, t in enumerate(horas_time):
					if isinstance(t, str) and t.startswith(fecha_ciudad):
						try:
							h_val = int(t.split("T")[1].split(":")[0])
							if h_val >= hora_actual:
								prob_h = 0
								prec_h = 0.0
								if idx_h < len(horas_prob) and horas_prob[idx_h] is not None:
									p_val = _safe_float(horas_prob[idx_h], 0.0)
									if not math.isnan(p_val) and not math.isinf(p_val):
										prob_h = max(0, min(100, int(p_val)))
								if idx_h < len(horas_prec) and horas_prec[idx_h] is not None:
									pr_val = _safe_float(horas_prec[idx_h], 0.0)
									if not math.isnan(pr_val) and not math.isinf(pr_val) and pr_val >= 0:
										prec_h = pr_val
								is_rain = (prob_h >= 15 or prec_h >= 0.1)
								
								if is_rain:
									if not currently_raining:
										rain_blocks += 1
										currently_raining = True
										if hora_exacta_lluvia is None:
											hora_exacta_lluvia = h_val
									if rain_blocks == 1:
										hora_fin_lluvia = h_val + 1
								else:
									currently_raining = False
						except Exception as e:
							log.debugWarning("ClimaAccesible: bloque lluvia ignorado: {}".format(e), exc_info=True)

			partes = [_("En {}, el reporte del clima es el siguiente.").format(city)]
			partes += self._frasesDelClimaActual(c, prefs)

			if prefs.get("minutos_lluvia"):
				m15 = data.get("minutely_15", {})
				m_times = m15.get("time", []) if isinstance(m15.get("time"), list) else []
				m_precs = m15.get("precipitation", []) if isinstance(m15.get("precipitation"), list) else []
				m_probs = m15.get("precipitation_probability", []) if isinstance(m15.get("precipitation_probability"), list) else []
				if m_times:
					import datetime
					try:
						if "time" in c and "T" in str(c["time"]):
							try:
								now_m = datetime.datetime.strptime(str(c["time"]).strip()[:16], "%Y-%m-%dT%H:%M")
							except Exception as e:
								log.debugWarning("ClimaAccesible: now_m fallback: {}".format(e), exc_info=True)
								now_m = datetime.datetime.now()
						else:
							now_m = datetime.datetime.now()
						prec_c = _safe_float(c.get("precipitation"), 0.0)
						if prec_c is None or math.isnan(prec_c) or math.isinf(prec_c) or prec_c < 0:
							prec_c = 0.0
						is_raining_now = prec_c > 0
						# Buscar un cambio en los próximos 120 minutos
						for i, t in enumerate(m_times):
							if i < len(m_precs) and isinstance(t, str):
								try:
									t_obj = datetime.datetime.strptime(t.strip()[:16], "%Y-%m-%dT%H:%M")
								except Exception as e:
									log.debugWarning("ClimaAccesible: minutely hora ignorada: {}".format(e), exc_info=True)
									continue
								diff_mins = (t_obj - now_m).total_seconds() / 60.0
								if 0 < diff_mins <= 120:
									prec_val = _safe_float(m_precs[i], 0.0)
									if prec_val is None or math.isnan(prec_val) or math.isinf(prec_val) or prec_val < 0:
										prec_val = 0.0
									prob_val = _safe_float(m_probs[i] if i < len(m_probs) else 0, 0.0)
									if prob_val is None or math.isnan(prob_val) or math.isinf(prob_val) or prob_val < 0:
										prob_val = 0.0
									
									if not is_raining_now and (prec_val >= 0.1 or prob_val >= 20):
										mins = int(round(diff_mins / 15.0) * 15)
										if mins == 0: mins = 15
										partes.append(_ngettext("Atención: La lluvia podría comenzar en unos {n} minuto.", "Atención: La lluvia podría comenzar en unos {n} minutos.", mins).format(n=mins))
										break
									elif is_raining_now and prec_val == 0 and prob_val < 15:
										mins = int(round(diff_mins / 15.0) * 15)
										if mins == 0: mins = 15
										partes.append(_ngettext("La lluvia se detendría en unos {n} minuto.", "La lluvia se detendría en unos {n} minutos.", mins).format(n=mins))
										break
					except Exception as e:
						log.debugWarning("ClimaAccesible: radar 15min ignorado: {}".format(e), exc_info=True)

			partes += self._frasesDelResumenDeHoy(c, dv, prefs, prob_max=prob_max_rest, lluvia_total=prec_total_rest, hora_exacta=hora_exacta_lluvia, hora_fin=hora_fin_lluvia, rain_blocks=rain_blocks)

			if len(partes) == 1:
				partes.append(_("No hay datos seleccionados. Abre la configuración con NVDA+Control+W."))

			if alertas_anexo:
				partes.append(alertas_anexo)

			self._safeMessage(" ".join(partes))

		except Exception as e:
			self._manejarErrorPeticion(e, operacion=_("el clima"))
		finally:
			try:
				with self._fetchLock:
					self._fetchingWeatherActive = False
			except AttributeError:
				self._fetchingWeatherActive = False

	def _urlDelClimaActual(self, lat, lon, prefs):
		"""Direccion a la que se le piden los datos del clima de ahora mismo.

		Solo se piden los datos marcados en la configuracion, para no pedirle al
		servicio lo que no se va a leer.
		"""
		current_fields = [api for k, _, api, t in OPCIONES if t == "current" and prefs.get(k, True)]
		if "weather_code" not in current_fields:
			current_fields.append("weather_code")
		if prefs.get("nieve", True) and "snow_depth" not in current_fields:
			current_fields.append("snow_depth")
		daily_fields   = [api for k, _, api, t in OPCIONES if t == "daily"   and prefs.get(k, True)]

		lat_f, lon_f = _coord_valida(lat, lon)

		q = {"latitude": lat_f, "longitude": lon_f, "wind_speed_unit": "kmh", "timezone": "auto", "forecast_days": 1}
		params = "?" + urllib.parse.urlencode(q)
		if current_fields:
			params += "&current=" + ",".join(current_fields)
		if prefs.get("minutos_lluvia", True):
			params += "&minutely_15=" + urllib.parse.quote("precipitation,precipitation_probability", safe=",")
		if daily_fields:
			params += "&daily=" + ",".join(daily_fields)
		params += "&hourly=" + urllib.parse.quote("precipitation_probability,precipitation", safe=",")

		url = "https://api.open-meteo.com/v1/forecast" + params
		return url

	def _urlCalidadAire(self, lat, lon, prefs):
		lat_f, lon_f = _coord_valida(lat, lon)
		aq_fields = []
		for k, _, api, t in OPCIONES:
			if t == "air_quality" and prefs.get(k, True):
				aq_fields.append(api)
		if not aq_fields:
			return None
		q = {"latitude": lat_f, "longitude": lon_f, "timezone": "auto"}
		return "https://air-quality-api.open-meteo.com/v1/air-quality?" + urllib.parse.urlencode(q) + "&current=" + ",".join(aq_fields)

	def _frasesDelClimaActual(self, c, prefs):
		"""Frases sobre como esta el tiempo en este momento.

		'c' son los datos actuales y 'prefs' lo que se quiere oir. Devuelve una
		lista de frases, que puede quedar vacia si no hay nada marcado.
		"""
		partes = []
		if prefs.get("temperatura") and c.get("temperature_2m") is not None:
			partes.append(_("Temperatura: {} grados Celsius.").format(c["temperature_2m"]))
		if prefs.get("sensacion") and c.get("apparent_temperature") is not None:
			temp_real = _safe_float(c.get("temperature_2m"))
			sens = c["apparent_temperature"]
			sens_f = _safe_float(sens)
			if temp_real is not None and sens_f is not None:
				# Solo decir la sensación térmica si difiere en más de 1.5 grados de la real (no obvio)
				if abs(temp_real - sens_f) > 1.5:
					partes.append(_("Sensación térmica: {} grados.").format(sens))
			else:
				partes.append(_("Sensación térmica: {} grados.").format(sens))
		cond_str = ""
		if prefs.get("condicion") and c.get("weather_code") is not None:
			cond_str = codigoClima(c["weather_code"])
			
		precip_val = 0.0
		if prefs.get("precipitacion"):
			raw_p = _safe_float(c.get("precipitation"), 0.0)
			precip_val = max(0.0, raw_p if raw_p is not None else 0.0)

		if cond_str and precip_val > 0:
			partes.append(_("Condición: {} (cayendo {} milímetros).").format(cond_str, precip_val))
		else:
			if cond_str:
				partes.append(_("Condición: {}.").format(cond_str))
			if precip_val > 0:
				partes.append(_("Precipitación actual: {} milímetros.").format(precip_val))

		if prefs.get("es_dia") and c.get("is_day") is not None:
			partes.append(_("Ahora es {}.").format(_("de día") if c["is_day"] == 1 else _("de noche")))
		
		if prefs.get("luna"):
			# Solo leer la luna si es de noche (is_day == 0) o si no hay datos de luz
			is_day = c.get("is_day")
			if is_day == 0 or is_day is None:
				import datetime
				fase = faseLunar(datetime.datetime.now())
				partes.append(_("Fase lunar: {}.").format(fase))
		if prefs.get("humedad") and c.get("relative_humidity_2m") is not None:
			partes.append(_("Humedad: {} por ciento.").format(c["relative_humidity_2m"]))
		if prefs.get("punto_rocio") and c.get("dew_point_2m") is not None:
			dew = c["dew_point_2m"]
			dew_f = _safe_float(dew)
			temp_f = _safe_float(c.get("temperature_2m"))
			if temp_f is not None and dew_f is not None:
				if abs(temp_f - dew_f) <= 2.0:
					partes.append(_("Punto de rocío crítico: {} grados (riesgo de niebla/humedad extrema).").format(dew))
			else:
				partes.append(_("Punto de rocío: {} grados.").format(dew))
		viento_vel = c.get("wind_speed_10m")
		if viento_vel is not None:
			v = _safe_float(viento_vel)
			if v is not None and v < 3.0:
				if prefs.get("viento_vel"):
					partes.append(_("Viento en calma."))
			elif v is not None:
				if prefs.get("viento_vel"):
					partes.append(_("Viento a {} kilómetros por hora.").format(viento_vel))
				if prefs.get("viento_dir") and c.get("wind_direction_10m") is not None:
					partes.append(_("Dirección del viento: {}.").format(cardinal(c["wind_direction_10m"])))
				if prefs.get("viento_rafagas") and c.get("wind_gusts_10m") is not None:
					rafagas = _safe_float(c["wind_gusts_10m"])
					if rafagas is not None and rafagas > v + 10:
						partes.append(_("Ráfagas de hasta {} kilómetros por hora.").format(c["wind_gusts_10m"]))
		if prefs.get("nubosidad") and c.get("cloud_cover") is not None:
			nube = _safe_float(c["cloud_cover"])
			if nube is not None:
				wc = c.get("weather_code", 99)
				try:
					wc = int(wc)
				except (ValueError, TypeError, OverflowError):
					wc = 99
				if not ((nube < 10 and wc in (0, 1)) or (nube > 90 and wc >= 3)):
					partes.append(_("Nubosidad: {} por ciento.").format(c["cloud_cover"]))
		if prefs.get("nieve"):
			try:
				snowfall = _safe_float(c.get("snowfall"), 0.0)
				snow_depth = _safe_float(c.get("snow_depth"), 0.0)
				if (snowfall is not None and snowfall > 0) or (snow_depth is not None and snow_depth > 0):
					sn_parts = []
					if snowfall and snowfall > 0: sn_parts.append(_("Nevada actual: {} centímetros").format(snowfall))
					if snow_depth and snow_depth > 0: sn_parts.append(_("Nieve acumulada en el suelo: {} metros").format(snow_depth))
					partes.append(". ".join(sn_parts) + ".")
			except (ValueError, TypeError, OverflowError) as e:
				log.debugWarning("ClimaAccesible: nieve ignorada: {}".format(e), exc_info=True)
		if prefs.get("visibilidad") and c.get("visibility") is not None:
			try:
				vis_m = _safe_float(c["visibility"])
				if vis_m is not None and 0 <= vis_m < 10000:
					if vis_m < 1000:
						partes.append(_("Visibilidad reducida: {} metros.").format(int(vis_m)))
					else:
						partes.append(_("Visibilidad reducida: {} kilómetros.").format(round(vis_m / 1000.0, 1)))
			except Exception as e:
				log.debugWarning("ClimaAccesible: visibilidad ignorada: {}".format(e), exc_info=True)
		if prefs.get("uv_actual") and c.get("uv_index") is not None:
			is_night = (c.get("is_day") == 0)
			uv_val = _safe_float(c.get("uv_index"), 0.0)
			if not (is_night and uv_val is not None and not math.isnan(uv_val) and uv_val <= 0.0):
				partes.append(_("Índice UV actual: {}.").format(c["uv_index"]))
		if prefs.get("calidad_aire") and c.get("european_aqi") is not None:
			val_aqi = c["european_aqi"]
			frase_aqi = calidadAireFrase(val_aqi)
			if frase_aqi:
				partes.append(_("Nivel de contaminación del aire: {} ({}).").format(val_aqi, frase_aqi))
			else:
				partes.append(_("Nivel de contaminación del aire: {}.").format(val_aqi))
		if prefs.get("elevacion") and c.get("elevation") is not None:
			elev_f = _safe_float(c.get("elevation"))
			if elev_f is not None:
				partes.append(_("Elevación: {} metros sobre el nivel del mar.").format(c["elevation"]))
		if prefs.get("presion") and c.get("surface_pressure") is not None:
			press_f = _safe_float(c.get("surface_pressure"))
			if press_f is not None and press_f > 0:
				partes.append(_("Presión atmosférica: {} hectopascales.").format(c["surface_pressure"]))
		return partes

	def _frasesDelResumenDeHoy(self, c, dv, prefs, prob_max=None, lluvia_total=None, hora_exacta=None, hora_fin=None, rain_blocks=0):
		"""Frases sobre como sera el resto del dia.

		Lo del amanecer y las horas de luz solo se dice con el cielo despejado: con
		nubes o lluvia no aporta nada y alarga el anuncio.
		"""
		partes = []
		codigo_raw = c.get("weather_code", 99)
		try:
			codigo_actual = int(codigo_raw)
		except (ValueError, TypeError, OverflowError):
			codigo_actual = 99
		cielo_despejado = codigo_actual in (0, 1)
		if cielo_despejado:
			if prefs.get("amanecer")  and dv("sunrise")           is not None:
				partes.append(_("Salida del sol: {}.").format(formatHora(dv("sunrise"))))
			if prefs.get("atardecer") and dv("sunset")            is not None:
				partes.append(_("Puesta del sol: {}.").format(formatHora(dv("sunset"))))
		if prefs.get("uv_max") and dv("uv_index_max") is not None:
			partes.append(_("Índice UV máximo del día: {}.").format(dv("uv_index_max")))
		if hora_exacta is not None:
			if rain_blocks > 1:
				partes.append(_("Se esperan lluvias intermitentes a lo largo del día, comenzando a las {} horas.").format(hora_exacta))
			elif hora_fin is not None and hora_fin > hora_exacta:
				if hora_fin == hora_exacta + 1:
					partes.append(_("Se esperan precipitaciones alrededor de las {} horas.").format(hora_exacta))
				else:
					if hora_fin == 24:
						partes.append(_("Se esperan precipitaciones desde las {} horas hasta la medianoche.").format(hora_exacta))
					else:
						partes.append(_("Se esperan precipitaciones desde las {} hasta las {} horas.").format(hora_exacta, hora_fin))
			else:
				partes.append(_("La lluvia o nevada podría comenzar a las {} horas.").format(hora_exacta))
		if lluvia_total is None:
			raw_lluvia = _safe_float(dv("precipitation_sum"), 0.0)
			lluvia_total = max(0.0, raw_lluvia if raw_lluvia is not None else 0.0)

		if prefs.get("precip_prob_max"):
			if prob_max is None:
				try:
					prob_max = int(float(dv("precipitation_probability_max") or 0))
				except (ValueError, TypeError, OverflowError):
					prob_max = 0
			if prob_max < 15 and lluvia_total < 0.1:
				partes.append(_("Sin lluvias."))
			else:
				partes.append(_("Probabilidad máxima de lluvia: {} por ciento.").format(prob_max))

		if prefs.get("precip_total") and lluvia_total > 0:
			partes.append(_("Precipitación total esperada del día: {} milímetros.").format(lluvia_total))
		if prefs.get("viento_max") and dv("wind_speed_10m_max") is not None:
			partes.append(_("Viento máximo del día: {} kilómetros por hora.").format(dv("wind_speed_10m_max")))
		if prefs.get("rafaga_max") and dv("wind_gusts_10m_max") is not None:
			partes.append(_("Ráfaga máxima del día: {} kilómetros por hora.").format(dv("wind_gusts_10m_max")))
		return partes


	# ── consulta pronóstico ───────────────────────────────────────────────────

	def _fetchForecast(self, cfg):
		"""Consulta el pronóstico de los próximos días y lo dice en voz alta.

		Igual que el clima actual, se ejecuta en segundo plano. Pide tantos días
		como tengas puesto en la configuración y arma una frase por día: nombre
		del día, cómo estará, máxima y mínima, viento, y lluvia si la hay. Cuando
		el día se espera despejado añade además a qué hora sale y se pone el sol.
		Los fallos de red se avisan con un mensaje que explica qué pasó.
		"""
		if getattr(self, "_fetchLock", None) is None or not hasattr(getattr(self, "_fetchLock", None), "acquire"):
			try:
				self._fetchLock = threading.Lock()
			except Exception:
				pass
		try:
			city          = cfg.get("city") or _("tu ciudad")
			lat           = cfg.get("lat")
			lon           = cfg.get("lon")
			try:
				forecast_days = max(1, min(16, int(cfg.get("forecast_days", 6))))
			except (ValueError, TypeError, OverflowError):
				forecast_days = 6
			prefs_raw = cfg.get("prefs", {})
			claves_validas = {op[0] for op in OPCIONES}
			prefs = {k: prefs_raw.get(k, True) for k in claves_validas}

			alertas_anexo_fc = []
			def fetch_alertas_fc():
				try:
					r = self._anexoAlertas(cfg)
					if r:
						alertas_anexo_fc.append(r)
				except Exception as e:
					log.debugWarning("ClimaAccesible: alertas en pronóstico ignoradas: {}".format(str(e)[:200]), exc_info=True)
			try:
				t_alertas = threading.Thread(target=fetch_alertas_fc, daemon=True)
				t_alertas.start()
			except Exception as e:
				log.debugWarning("ClimaAccesible: no se pudo iniciar hilo de alertas: {}".format(e), exc_info=True)
				t_alertas = None

			url = self._urlDelPronostico(lat, lon, forecast_days)
			data = self._getJsonFromApi(url, "pronóstico")
			if self._stopping.is_set():
				return
			if not data:
				self._safeMessage(_("No se recibieron datos. Comprueba tu conexión a Internet."))
				return

			d           = data.get("daily") if isinstance(data.get("daily"), dict) else {}
			h           = data.get("hourly") if isinstance(data.get("hourly"), dict) else {}
			c_now       = data.get("current") if isinstance(data.get("current"), dict) else {}
			codigo_now  = c_now.get("weather_code")
			horas_time  = h.get("time",                          []) if isinstance(h.get("time"), list) else []
			horas_code  = h.get("weather_code",                  []) if isinstance(h.get("weather_code"), list) else []
			horas_prob  = h.get("precipitation_probability",     []) if isinstance(h.get("precipitation_probability"), list) else []
			horas_prec  = h.get("precipitation",                 []) if isinstance(h.get("precipitation"), list) else []
			fechas      = d.get("time") if isinstance(d.get("time"), (list, tuple)) else []
			if not fechas:
				self._safeMessage(_("No se recibieron datos del pronóstico para {}.").format(city))
				return
			codigos     = d.get("weather_code") if isinstance(d.get("weather_code"), (list, tuple)) else []
			temp_max    = d.get("temperature_2m_max") if isinstance(d.get("temperature_2m_max"), (list, tuple)) else []
			temp_min    = d.get("temperature_2m_min") if isinstance(d.get("temperature_2m_min"), (list, tuple)) else []
			viento_max  = d.get("wind_speed_10m_max") if isinstance(d.get("wind_speed_10m_max"), (list, tuple)) else []
			prob_precip = d.get("precipitation_probability_max") if isinstance(d.get("precipitation_probability_max"), (list, tuple)) else []
			precip_sum  = d.get("precipitation_sum") if isinstance(d.get("precipitation_sum"), (list, tuple)) else []
			amaneceres  = d.get("sunrise") if isinstance(d.get("sunrise"), (list, tuple)) else []
			atardeceres = d.get("sunset") if isinstance(d.get("sunset"), (list, tuple)) else []
			partes = [_("Pronóstico para {} para los próximos {} días.").format(city, len(fechas))]

			# Detectar la hora actual para el pronostico de hoy (usando hora local reportada por la API si existe)
			if c_now and "time" in c_now:
				try:
					hora_actual_hoy = int(str(c_now["time"]).split("T")[1].split(":")[0])
				except Exception as e:
					log.debugWarning("ClimaAccesible: hora hoy fallback: {}".format(e), exc_info=True)
					hora_actual_hoy = datetime.datetime.now().hour
			else:
				hora_actual_hoy = datetime.datetime.now().hour

			for i, fecha in enumerate(fechas):
				label     = self._nombreDeDia(fecha, i)
				codigo    = codigos[i]     if i < len(codigos)     else None
				tmax      = temp_max[i]    if (i < len(temp_max) and temp_max[i] is not None)       else "?"
				tmin      = temp_min[i]    if (i < len(temp_min) and temp_min[i] is not None)       else "?"
				vmax      = viento_max[i]  if (i < len(viento_max) and viento_max[i] is not None)   else "?"
				prob_p    = prob_precip[i] if i < len(prob_precip) else None
				prec_s    = precip_sum[i]  if i < len(precip_sum)  else None
				_hora_desc = _("hora desconocida")
				amanecer  = formatHora(amaneceres[i])  if i < len(amaneceres)  else _hora_desc
				atardecer = formatHora(atardeceres[i]) if i < len(atardeceres) else _hora_desc

				# Para el dia de hoy (i == 0), evaluar unicamente las horas que quedan
				hora_filtro = hora_actual_hoy if i == 0 else None

				hora_exacta = None
				hora_fin = None
				rain_blocks = 0
				currently_raining = False
				if horas_time:
					probs_rest = []
					precs_rest = []
					codigos_rest = []
					for idx_h, t in enumerate(horas_time):
						if not isinstance(t, str) or not t.startswith(str(fecha)):
							continue
						try:
							hora_h = int(t.split("T")[1].split(":")[0])
						except Exception as e:
							log.debugWarning("ClimaAccesible: hora pronóstico ignorada: {}".format(e), exc_info=True)
							continue
						if hora_filtro is not None and hora_h < hora_filtro:
							continue
						prob_h = 0
						prec_h = 0.0
						if idx_h < len(horas_prob) and horas_prob[idx_h] is not None:
							try:
								p_num = float(horas_prob[idx_h])
								if not math.isnan(p_num) and not math.isinf(p_num):
									prob_h = max(0, min(100, int(p_num)))
									probs_rest.append(prob_h)
							except (ValueError, TypeError, OverflowError) as e:
								log.debugWarning("ClimaAccesible: prob hora ignorada: {}".format(e), exc_info=True)
						if idx_h < len(horas_prec) and horas_prec[idx_h] is not None:
							try:
								pr_num = float(horas_prec[idx_h])
								if not math.isnan(pr_num) and not math.isinf(pr_num) and pr_num >= 0:
									prec_h = pr_num
									precs_rest.append(prec_h)
							except (ValueError, TypeError, OverflowError) as e:
								log.debugWarning("ClimaAccesible: prec hora ignorada: {}".format(e), exc_info=True)
						if prefs.get("hora_lluvia"):
							is_rain = (prob_h >= 15 or prec_h >= 0.1)
							if is_rain:
								if not currently_raining:
									rain_blocks += 1
									currently_raining = True
									if hora_exacta is None:
										hora_exacta = hora_h
								if rain_blocks == 1:
									hora_fin = hora_h + 1
							else:
								currently_raining = False

						# Actualizar el codigo meteorologico de hoy considerando las horas restantes y el clima
						# actual, evitando arrastrar codigos de lluvia o llovizna de horas pasadas de la madrugada.
						if idx_h < len(horas_code) and horas_code[idx_h] is not None:
							try:
								codigos_rest.append(int(horas_code[idx_h]))
							except (ValueError, TypeError, OverflowError) as e:
								log.debugWarning("ClimaAccesible: código hora ignorado: {}".format(e), exc_info=True)
					if probs_rest:
						prob_p = max(probs_rest)
					if precs_rest:
						prec_s = round(sum(precs_rest), 1)
					if codigos_rest:
						candidatos = codigos_rest.copy()
						if codigo_now is not None:
							try:
								candidatos.append(int(codigo_now))
							except (ValueError, TypeError, OverflowError) as e:
								log.debugWarning("ClimaAccesible: código actual ignorado: {}".format(e), exc_info=True)
						codigo = max(candidatos)
					elif codigo_now is not None:
						try:
							codigo = int(codigo_now)
						except (ValueError, TypeError, OverflowError) as e:
							log.debugWarning("ClimaAccesible: código now ignorado: {}".format(e), exc_info=True)

				cond = codigoClima(codigo) if codigo is not None else _("condición desconocida")
				lluvia_info = self._fraseDeLluvia(prob_p, prec_s, hora_exacta, hora_fin, rain_blocks)

				con_sol = (codigo in (0, 1) and amanecer != _hora_desc and atardecer != _hora_desc) if codigo is not None else False

				calcadas = False
				t_avg = None
				if tmax != "?" and tmin != "?":
					try:
						tmax_f = _safe_float(tmax)
						tmin_f = _safe_float(tmin)
						if (
							tmax_f is not None and tmin_f is not None
							and not math.isnan(tmax_f) and not math.isinf(tmax_f)
							and not math.isnan(tmin_f) and not math.isinf(tmin_f)
							and abs(tmax_f - tmin_f) <= 1.5
						):
							t_avg = int(round((tmax_f + tmin_f) / 2.0))
							calcadas = True
					except Exception as e:
						log.debugWarning("ClimaAccesible: t_avg fallo: {}".format(e), exc_info=True)
				
				if calcadas and t_avg is not None:
					temp_str = _("Temperatura constante rondando los {} grados").format(t_avg)
				else:
					temp_str = _("Máxima {} grados, mínima {} grados").format(tmax, tmin)

				fase_str = ""
				if prefs.get("luna"):
					import datetime
					try:
						t_obj = datetime.datetime.strptime(fecha, "%Y-%m-%d")
						fase_str = _(" Fase lunar: {}.").format(faseLunar(t_obj))
					except Exception as e:
						log.debugWarning("ClimaAccesible: fase lunar ignorada: {}".format(e), exc_info=True)

				try:
					if con_sol:
						partes.append(
							_("{}: {}. {}. "
							"Viento máximo {} kilómetros por hora.{}"
							" Sol visible de {} a {}.{}").format(
								label, cond, temp_str, vmax, lluvia_info, amanecer, atardecer, fase_str
							)
						)
					else:
						partes.append(
							_("{}: {}. {}. "
							"Viento máximo {} kilómetros por hora.{}{}").format(
								label, cond, temp_str, vmax, lluvia_info, fase_str
							)
						)
				except Exception as fmt_err:
					log.warning("ClimaAccesible: Error formateando frase del día '{}': {}".format(str(label)[:80], fmt_err))
					partes.append("{}: {}. {}.".format(label, cond, temp_str))

			if t_alertas is not None:
				t_alertas.join(timeout=5.0)
			if alertas_anexo_fc:
				partes.append(alertas_anexo_fc[0])

			self._safeMessage(" ".join(partes))

		except Exception as e:
			self._manejarErrorPeticion(e, operacion=_("el pronóstico"))
		finally:
			try:
				with self._fetchLock:
					self._fetchingForecastActive = False
			except AttributeError:
				self._fetchingForecastActive = False

	def _urlDelPronostico(self, lat, lon, forecast_days):
		"""Direccion a la que se le piden los datos del pronostico."""
		lat_f, lon_f = _coord_valida(lat, lon)
		try:
			days = max(1, min(16, int(forecast_days)))
		except (ValueError, TypeError, OverflowError):
			days = 6
		q = {"latitude": lat_f, "longitude": lon_f, "wind_speed_unit": "kmh", "timezone": "auto", "forecast_days": days}
		url = (
			"https://api.open-meteo.com/v1/forecast?"
			+ urllib.parse.urlencode(q)
			+ "&daily=" + ",".join(["weather_code", "temperature_2m_max", "temperature_2m_min",
			"precipitation_sum", "precipitation_probability_max", "wind_speed_10m_max", "sunrise", "sunset", "snowfall_sum", "precipitation_hours"])
			+ "&hourly=" + urllib.parse.quote("weather_code,precipitation_probability,precipitation", safe=",")
			+ "&current=" + urllib.parse.quote("weather_code", safe=",")
		)
		return url

	def _nombreDeDia(self, fecha_str, idx):
		"""Como se nombra un dia del pronostico: hoy, manana, o su fecha.

		Las listas de dias y meses se arman aqui dentro, y no fuera, porque sus
		nombres se traducen y la traduccion no esta lista hasta que NVDA arranca.
		Se indexan numericamente para no depender de la configuracion regional (locale)
		del sistema operativo anfitrion.
		"""
		DIAS_ES = [
			_("lunes"), _("martes"), _("miércoles"),
			_("jueves"), _("viernes"), _("sábado"), _("domingo"),
		]
		MESES_ES = [
			"", _("enero"), _("febrero"), _("marzo"),
			_("abril"), _("mayo"), _("junio"),
			_("julio"), _("agosto"), _("septiembre"),
			_("octubre"), _("noviembre"), _("diciembre"),
		]

		if idx == 0: return _("hoy")
		if idx == 1: return _("mañana")
		try:
			dt  = datetime.date.fromisoformat(fecha_str)
			dia = DIAS_ES[dt.weekday()]
			mes = MESES_ES[dt.month]
			return _("{} {} de {}").format(dia, dt.day, mes)
		except Exception as e:
			log.debugWarning("ClimaAccesible: _nombreDeDia fallback: {}".format(e), exc_info=True)
			try:
				return str(fecha_str)
			except Exception as e2:
				log.debugWarning("ClimaAccesible: _nombreDeDia str fallo: {}".format(e2), exc_info=True)
				return "?"

	def _fraseDeLluvia(self, prob_p, prec_s, hora_exacta=None, hora_fin=None, rain_blocks=0):
		"""Como se cuenta la lluvia de un dia, segun lo que se sepa de ella.

		Se dice la probabilidad, los milimetros, los dos o ninguno, y se anade el
		momento del dia cuando se conoce. Devuelve cadena vacia si no hay lluvia.
		"""
		lluvia_info = ""
		try:
			prob_val = int(float(prob_p)) if prob_p is not None else 0
			prob_val = max(0, min(100, prob_val))
		except (ValueError, TypeError, OverflowError):
			prob_val = 0
		try:
			prec_val = float(prec_s) if prec_s is not None else 0.0
			if math.isnan(prec_val) or math.isinf(prec_val) or prec_val < 0:
				prec_val = 0.0
		except (ValueError, TypeError, OverflowError):
			prec_val = 0.0

		# Una probabilidad inferior al 15% sin acumulación medible (< 0.1 mm) se considera
		# meteorológicamente ausencia de precipitaciones, evitando falsos anuncios de lluvia
		# residuales (como 1% o 2%).
		if prob_val < 15 and prec_val < 0.1:
			return ""

		if hora_exacta is not None:
			try:
				hora_exacta = int(hora_exacta)
				if not (0 <= hora_exacta <= 23):
					hora_exacta = None
			except (ValueError, TypeError, OverflowError):
				hora_exacta = None

		if hora_fin is not None:
			try:
				hora_fin = int(hora_fin)
				if not (1 <= hora_fin <= 24):
					hora_fin = None
			except (ValueError, TypeError, OverflowError):
				hora_fin = None

		momento_str = ""
		if hora_exacta is not None:
			if rain_blocks > 1:
				momento_str = _(" (lluvias intermitentes desde las {} horas)").format(hora_exacta)
			elif hora_fin is not None and hora_fin > hora_exacta:
				if hora_fin == hora_exacta + 1:
					momento_str = _(" (alrededor de las {} horas)").format(hora_exacta)
				elif hora_fin == 24:
					momento_str = _(" (desde las {} horas hasta la medianoche)").format(hora_exacta)
				else:
					momento_str = _(" (desde las {} hasta las {} horas)").format(hora_exacta, hora_fin)
			else:
				momento_str = _(" (comenzando a las {} horas)").format(hora_exacta)

		if prob_val >= 15 and prec_val >= 0.1:
			lluvia_info = _(" Probabilidad máxima de lluvia: {} por ciento{} con {} milímetros.").format(prob_val, momento_str, prec_val)
		elif prob_val >= 15:
			lluvia_info = _(" Probabilidad máxima de lluvia: {} por ciento{}.").format(prob_val, momento_str)
		elif prec_val >= 0.1:
			lluvia_info = _(" Precipitación esperada{} de {} milímetros.").format(momento_str, prec_val)
		return lluvia_info


	def _startupBackgroundWorker(self):
		"""Comprueba en segundo plano tras iniciar NVDA si existen conflictos con otros complementos."""
		try:
			if self._stopping.wait(timeout=3.0):
				return
			try:
				getGeoData()
			except Exception as ge:
				log.debug(f"ClimaAccesible: pre-carga de geodata: {ge}")
			if self._stopping.is_set():
				return
			self._checkAddonConflicts(interactive=False)
		except Exception as e:
			log.error(f"ClimaAccesible: Error durante la comprobación de conflictos: {e}")

	def auditConflicts(self):
		"""
		Audita y registra en nvda.log posibles conflictos con otros complementos instalados o activos,
		incluyendo colisiones directas de atajos de teclado (gestos) y complementos de clima duplicados.
		Devuelve una tupla (conflicts, warnings).
		"""
		conflicts = []
		warnings = []

		def _normalizarGesto(gesto_str):
			"""Normaliza un gesto de teclado eliminando espacios y modificadores redundantes."""
			s = str(gesto_str).strip().lower().replace(" ", "")
			return re.sub(r'\(.*?\)', '', s)

		default_map = {
			"kb:nvda+w": _("Lectura del clima actual"),
			"kb:nvda+shift+w": _("Lectura del pronóstico extendido"),
			"kb:nvda+control+w": _("Ventana de configuración del clima"),
		}
		our_gestures_map = {}
		g_map = getattr(self, "_gestureMap", {}) or {}
		if g_map:
			for g_id, script_ref in g_map.items():
				norm_g = _normalizarGesto(g_id)
				desc = getattr(script_ref, "description", "") or getattr(script_ref, "__doc__", "") or default_map.get(norm_g, getattr(script_ref, "__name__", str(script_ref)))
				our_gestures_map[norm_g] = desc
		else:
			our_gestures_map = {_normalizarGesto(k): v for k, v in default_map.items()}

		log.info("ClimaAccesible: Iniciando auditoría de compatibilidad y detección de conflictos...")

		# 1. Comprobar complementos de clima duplicados o conocidos
		known_overlapping = {
			"weatherplus": _("Weather Plus (superpone atajos globales de clima como NVDA+W)"),
			"weather": _("Weather (superpone atajos globales de información meteorológica)"),
			"weatherupdate": _("Weather Update"),
		}

		try:
			available_addons = list(addonHandler.getAvailableAddons())
			for addon in available_addons:
				addon_name = getattr(addon, "name", "").lower()
				if addon_name == "climaaccesible":
					continue

				if getattr(addon, "isDisabled", False):
					continue

				manifest = getattr(addon, "manifest", {}) or {}
				summary = manifest.get("summary", "")

				if addon_name in known_overlapping:
					reason = known_overlapping[addon_name]
					msg = f"Complemento de clima activo detectado: '{addon.name}' ({summary}). Motivo: {reason}."
					warnings.append(msg)
					log.warning(f"ClimaAccesible ADVERTENCIA DE COMPATIBILIDAD: {msg}")
				elif re.search(r'\b(clima|weather|meteorol\w*)\b', summary, re.IGNORECASE):
					msg = f"Complemento meteorológico alternativo activo: '{addon.name}' ({summary}). Podría compartir atajos como NVDA+W."
					warnings.append(msg)
					log.warning(f"ClimaAccesible ADVERTENCIA DE COMPATIBILIDAD: {msg}")
		except Exception as e:
			log.debug(f"ClimaAccesible: No se pudo verificar la lista de complementos instalados: {e}")

		# 2. Comprobar colisiones directas de atajos con otros plugins globales
		# Nota: "_gestureMap" y "_ScriptableObject__gestures" son detalles internos de NVDA,
		# no una forma oficial y garantizada de leer los atajos de otro complemento. Si una
		# futura versión de NVDA les cambia el nombre, esta detección de conflictos dejaría
		# de encontrar cosas (sin afectar al resto del complemento), y habría que revisarla.
		try:
			running = getattr(globalPluginHandler, "runningPlugins", set())
			for plugin in running:
				if plugin is self:
					continue
				plugin_mod = getattr(plugin, "__module__", str(type(plugin)))
				if "climaaccesible" in plugin_mod.lower():
					continue

				g_map = getattr(plugin, "_gestureMap", {}) or {}
				if not g_map:
					g_map = getattr(plugin, "_ScriptableObject__gestures", {}) or {}

				for g_id, script_ref in g_map.items():
					norm_g = _normalizarGesto(g_id)
					if norm_g in our_gestures_map:
						script_name = getattr(script_ref, "__name__", str(script_ref))
						our_feature = our_gestures_map[norm_g]
						collision_msg = (
							f"Colisión de atajo: '{norm_g}' está asignado simultáneamente a '{our_feature}' (ClimaAccesible) "
							f"y a '{script_name}' en el plugin '{plugin_mod}'."
						)
						conflicts.append(collision_msg)
						log.warning(f"ClimaAccesible CONFLICTO DE ATAJO: {collision_msg}")
		except Exception as e:
			log.debug(f"ClimaAccesible: Error inspeccionando runningPlugins: {e}")

		# 3. Comprobar colisiones con comandos globales de NVDA
		try:
			import globalCommands
			cmd_obj = getattr(globalCommands, "commands", None)
			if cmd_obj:
				cmd_map = getattr(cmd_obj, "_gestureMap", {}) or {}
				for cmd_g, cmd_script in cmd_map.items():
					norm_cmd = _normalizarGesto(cmd_g)
					if norm_cmd in our_gestures_map:
						our_feature = our_gestures_map[norm_cmd]
						cmd_desc = getattr(cmd_script, "description", "") or getattr(cmd_script, "__name__", str(cmd_script))
						collision_msg = (
							f"Colisión de atajo: '{norm_cmd}' está asignado simultáneamente a '{our_feature}' (ClimaAccesible) "
							f"y al comando nativo de NVDA '{cmd_desc}'."
						)
						conflicts.append(collision_msg)
						log.warning(f"ClimaAccesible CONFLICTO CON NVDA CORE: {collision_msg}")
		except Exception as e:
			log.debug(f"ClimaAccesible: No se pudo verificar comandos globales nativos: {e}")

		# Resumen final en el log
		total_issues = len(conflicts) + len(warnings)
		if total_issues == 0:
			log.info("ClimaAccesible: Auditoría de conflictos finalizada con éxito. No se detectaron colisiones de atajos ni complementos incompatibles activos.")
		else:
			log.warning(
				f"ClimaAccesible: Auditoría de conflictos finalizada. Se detectaron {len(conflicts)} colisión(es) directa(s) de atajos "
				f"y {len(warnings)} advertencia(s) de compatibilidad."
			)

		return conflicts, warnings

	def _checkAddonConflicts(self, interactive=False):
		"""Revisa si otro complemento choca con este.

		Pide la lista a auditConflicts(). Con interactive en False solo la deja
		anotada en el registro de NVDA; así se usa al arrancar, sin molestar. Con
		interactive en True abre un cuadro de mensaje que explica qué atajos de
		teclado están repetidos y qué otros complementos de clima podrían estorbar,
		o avisa de que no hay ninguno.
		"""
		conflicts, warnings = self.auditConflicts()
		if interactive:
			total = len(conflicts) + len(warnings)
			if total == 0:
				gui.messageBox(
					_("No se han detectado conflictos de atajos de teclado ni complementos incompatibles de clima activos en este sistema."),
					_("Auditoría de compatibilidad - ClimaAccesible"),
					wx.OK | wx.ICON_INFORMATION,
				)
			else:
				lines = []
				if conflicts:
					lines.append(_("COLISIONES DIRECTAS DE ATAJOS:"))
					for c in conflicts:
						lines.append(f"• {c}")
				if warnings:
					if lines:
						lines.append("")
					lines.append(_("ADVERTENCIAS DE COMPATIBILIDAD:"))
					for w in warnings:
						lines.append(f"• {w}")
				lines.append("")
				lines.append(_("Nota: Los detalles completos también se han registrado en el archivo de log de NVDA."))
				gui.messageBox(
					"\n".join(lines),
					_("Auditoría de compatibilidad - ClimaAccesible"),
					wx.OK | wx.ICON_WARNING,
				)

	def _onMenuConflicts(self, event):
		"""Manejador de evento del menú para ejecutar la comprobación interactiva de conflictos."""
		wx.CallAfter(self._checkAddonConflicts, interactive=True)

	@scriptHandler.script(
		description=_("Comprueba si existen conflictos de atajos de teclado o complementos incompatibles con ClimaAccesible."),
		category=scriptCategory,
	)
	def script_checkConflicts(self, gesture):
		"""Ejecuta una comprobación interactiva de atajos de teclado y complementos concurrentes."""
		wx.CallAfter(self._checkAddonConflicts, interactive=True)

