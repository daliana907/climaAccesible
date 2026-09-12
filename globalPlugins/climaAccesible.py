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
import globalVars
import core
from logHandler import log

# ── rutas de archivos ─────────────────────────────────────────────────────────
_ADDON_DIR   = os.path.dirname(__file__)
GEODATA_FILE = os.path.join(_ADDON_DIR, "geodata.json")

def _configPath():
	"""Devuelve la ruta correcta para guardar la configuración en el perfil de NVDA."""
	return os.path.join(globalVars.appArgs.configPath, "climaAccesible.json")

# ── caché de datos geográficos ────────────────────────────────────────────────
_geoData = None

# ── opciones de datos del clima ───────────────────────────────────────────────
def N_(texto):
	"""Marca un texto para que el extractor de traducciones lo recoja.

	Se usa en las tablas que se crean al cargar el complemento: ahí no se puede
	traducir todavía, así que se traduce con _() en el momento de mostrarlo.
	"""
	return texto


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
	("precipitacion",   N_("Precipitación actual"),                     "precipitation",                  "current"),
	("presion",         N_("Presión atmosférica"),                      "surface_pressure",               "current"),
	("amanecer",        N_("Hora de salida del sol"),                   "sunrise",                        "daily"),
	("atardecer",       N_("Hora de puesta del sol"),                   "sunset",                         "daily"),
	("horas_luz",       N_("Horas de luz solar del día"),               "daylight_duration",              "daily"),
	("uv_max",          N_("Índice UV máximo del día"),                 "uv_index_max",                   "daily"),
	("precip_prob_max", N_("Probabilidad máxima de lluvia del día"),    "precipitation_probability_max", "daily"),
	("precip_total",    N_("Precipitación total esperada del día"),     "precipitation_sum",              "daily"),
	("viento_max",      N_("Viento máximo del día"),                    "wind_speed_10m_max",             "daily"),
	("rafaga_max",      N_("Ráfaga máxima del día"),                    "wind_gusts_10m_max",             "daily"),
]

PREFS_DEFECTO = {op[0]: True for op in OPCIONES}

# ── helpers ───────────────────────────────────────────────────────────────────

def loadJSON(path):
	"""Carga un archivo JSON desde el disco de forma segura.

	Si el archivo no existe o está corrupto, captura el error, deja una nota
	en el registro de NVDA para no interrumpir al usuario y devuelve un diccionario
	vacío para que el resto del complemento pueda seguir funcionando sin fallar.
	"""
	try:
		if os.path.exists(path):
			with open(path, "r", encoding="utf-8") as f:
				return json.load(f)
	except Exception as e:
		log.warning("ClimaAccesible: error al leer {}: {}".format(path, e))
	return {}

def saveJSON(path, data):
	"""Guarda datos en un archivo JSON en el disco con formato legible y codificación UTF-8.

	Usa sangría de dos espacios y asegura que los caracteres con tildes o caracteres
	especiales no se escapen en secuencias raras de Unicode, para que el usuario o
	desarrollador pueda leer el archivo directamente si lo abre.
	"""
	try:
		with open(path, "w", encoding="utf-8") as f:
			json.dump(data, f, ensure_ascii=False, indent=2)
	except Exception as e:
		log.error("ClimaAccesible: error al guardar {}: {}".format(path, e))

def getGeoData():
	"""Obtiene la base de datos geográfica local (países, regiones y ciudades).

	Para que la ventana de configuración abra rápido y no lea el disco cada vez,
	mantiene los datos en memoria una vez cargados (patrón Singleton / caché).
	Si todavía no se han leído, abre geodata.json y los carga.
	"""
	global _geoData
	if _geoData is None:
		try:
			with open(GEODATA_FILE, "r", encoding="utf-8") as f:
				_geoData = json.load(f)
		except Exception as e:
			log.error("ClimaAccesible: no se pudo cargar geodata.json: {}".format(e))
			raise
	return _geoData

def formatHora(iso_str):
	"""Extrae la hora y los minutos de una fecha con formato ISO 8601 (ejemplo: 2026-09-12T14:30).

	Devuelve solo la parte '14:30' para que NVDA la lea de forma clara y limpia sin
	atiborrar al usuario con fechas largas o segundos innecesarios.
	"""
	try:
		return iso_str.split("T")[1][:5]
	except Exception:
		return str(iso_str)

def formatSegundos(seg):
	"""Convierte una cantidad de segundos en una frase natural de horas y minutos.

	Por ejemplo, convierte la duración de luz solar en '11 horas y 45 minutos'.
	Si solo son horas completas omite los minutos, y si es menos de una hora solo
	menciona los minutos, para que el sintetizador suene natural al hablar.
	"""
	try:
		seg = int(float(seg))
		h   = seg // 3600
		m   = (seg % 3600) // 60
		if h > 0 and m > 0:
			return _("{} horas y {} minutos").format(h, m)
		elif h > 0:
			return _("{} horas").format(h)
		else:
			return _("{} minutos").format(m)
	except Exception:
		return str(seg)

def cardinal(deg):
	"""Convierte los grados de una veleta (0 a 360) en el punto cardinal correspondiente.

	Divide la rosa de los vientos en 16 sectores de 22.5 grados cada uno (Norte,
	Nor-Noreste, Noreste, etc.) para que quien use el lector de pantalla sepa de
	dónde viene el viento de forma intuitiva sin tener que interpretar números de grados.
	"""
	if deg is None:
		return _("dirección desconocida")
	dirs = [
		_("norte"), _("nor noreste"), _("noreste"), _("este noreste"),
		_("este"), _("este sureste"), _("sureste"), _("sur sureste"),
		_("sur"), _("sur suroeste"), _("suroeste"), _("oeste suroeste"),
		_("oeste"), _("oeste noroeste"), _("noroeste"), _("nor noroeste"),
	]
	return dirs[round(deg / 22.5) % 16]

def codigoClima(code):
	"""Traduce el código numérico meteorológico de la OMM (WMO) a una descripción en español.

	Los servicios como Open-Meteo devuelven códigos estándar internacionales
	(por ejemplo: 0 para despejado, 61 para lluvia ligera, 95 para tormenta).
	Esta función los mapea a textos accesibles y comprensibles al oído.
	"""
	m = {
		0:_("cielo despejado"),       1:_("mayormente despejado"),   2:_("parcialmente nublado"),
		3:_("nublado"),               45:_("niebla"),                48:_("niebla con escarcha"),
		51:_("llovizna ligera"),      53:_("llovizna moderada"),     55:_("llovizna densa"),
		61:_("lluvia ligera"),        63:_("lluvia moderada"),       65:_("lluvia intensa"),
		71:_("nevada ligera"),        73:_("nevada moderada"),       75:_("nevada intensa"),
		77:_("granizo fino"),         80:_("chubascos ligeros"),     81:_("chubascos moderados"),
		82:_("chubascos intensos"),   85:_("chubascos de nieve ligeros"),
		86:_("chubascos de nieve intensos"),
		95:_("tormenta eléctrica"),   96:_("tormenta con granizo ligero"),
		99:_("tormenta con granizo intenso"),
	}
	return m.get(code, _("condición desconocida"))

def momentoLluvia(fecha, hourly_times, hourly_probs, hourly_precs):
	"""
	Analiza los datos horarios del día y devuelve una frase natural
	indicando el momento en que se espera lluvia ('por la mañana', 'por la tarde',
	'por la noche', 'por la tarde y por la noche', 'durante todo el día', etc.).
	"""
	if not hourly_times:
		return ""

	madrugada = False
	manana    = False
	tarde     = False
	noche     = False

	probs = hourly_probs if hourly_probs else [0] * len(hourly_times)
	precs = hourly_precs if hourly_precs else [0.0] * len(hourly_times)

	for t, prob, prec in zip(hourly_times, probs, precs):
		if not t.startswith(fecha):
			continue
		try:
			hour = int(t.split("T")[1].split(":")[0])
		except Exception:
			continue

		prob_val = int(prob) if prob is not None else 0
		prec_val = float(prec) if prec is not None else 0.0

		if prob_val >= 20 or prec_val >= 0.1:
			if 0 <= hour < 6:
				madrugada = True
			elif 6 <= hour < 12:
				manana = True
			elif 12 <= hour < 20:
				tarde = True
			else:
				noche = True

	periodos = []
	if madrugada:
		periodos.append(_("la madrugada"))
	if manana:
		periodos.append(_("la mañana"))
	if tarde:
		periodos.append(_("la tarde"))
	if noche:
		periodos.append(_("la noche"))

	if not periodos:
		return ""
	if len(periodos) >= 3 or (manana and tarde and (noche or madrugada)):
		return _("durante todo el día")
	if len(periodos) == 1:
		return _("por {}").format(periodos[0])
	if len(periodos) == 2:
		return _("por {} y por {}").format(periodos[0], periodos[1])
	return _("por {} y por {}").format(", ".join(periodos[:-1]), periodos[-1])


# ── diálogo de configuración ──────────────────────────────────────────────────

class ConfigDialog(wx.Dialog):

	def __init__(self, parent):
		super(ConfigDialog, self).__init__(
			parent,
			title=_("ClimaAccesible - Configuración"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
		)
		self._isClosing = False
		self._countries = []
		self._regions   = []
		self._cities    = []
		self._cfg       = loadJSON(_configPath())
		self._checks    = {}
		self._build_ui()
		self.btnCancel.SetFocus()
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

		sizer_loc.Add(wx.StaticText(p, label=_("País:")), 0, wx.LEFT|wx.TOP, 4)
		self.cboCountry = wx.ComboBox(p, style=wx.CB_READONLY, size=(420, -1))
		self.cboCountry.Disable()
		self.cboCountry.Bind(wx.EVT_COMBOBOX, self.onCountryChange)
		sizer_loc.Add(self.cboCountry, 0, wx.LEFT|wx.RIGHT, 4)

		sizer_loc.Add(wx.StaticText(p, label=_("Departamento / Región:")), 0, wx.LEFT|wx.TOP, 4)
		self.cboRegion = wx.ComboBox(p, style=wx.CB_READONLY, size=(420, -1))
		self.cboRegion.Disable()
		self.cboRegion.Bind(wx.EVT_COMBOBOX, self.onRegionChange)
		sizer_loc.Add(self.cboRegion, 0, wx.LEFT|wx.RIGHT, 4)

		sizer_loc.Add(wx.StaticText(p, label=_("Ciudad:")), 0, wx.LEFT|wx.TOP, 4)
		self.cboCity = wx.ComboBox(p, style=wx.CB_READONLY, size=(420, -1))
		self.cboCity.Disable()
		self.cboCity.Bind(wx.EVT_COMBOBOX, self.onCityChange)
		sizer_loc.Add(self.cboCity, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 4)

		self.progressBar = wx.Gauge(p, range=100, size=(420, 18), style=wx.GA_HORIZONTAL|wx.GA_SMOOTH)
		sizer_loc.Add(self.progressBar, 0, wx.LEFT|wx.RIGHT, 4)
		self.lblStatus = wx.StaticText(p, label=_("Cargando datos..."))
		sizer_loc.Add(self.lblStatus, 0, wx.LEFT|wx.TOP|wx.BOTTOM, 4)
		main.Add(sizer_loc, 0, wx.EXPAND|wx.ALL, 8)

		# ── datos actuales ────────────────────────────────────────────────────
		prefs  = self._cfg.get("prefs", dict(PREFS_DEFECTO))
		box_c  = wx.StaticBox(p, label=_("Datos actuales que quiero escuchar"))
		sizer_c = wx.StaticBoxSizer(box_c, wx.VERTICAL)
		for key, label, campoApi, tipo in OPCIONES:
			if tipo == "current":
				cb = wx.CheckBox(p, label=label)
				cb.SetValue(prefs.get(key, True))
				self._checks[key] = cb
				sizer_c.Add(cb, 0, wx.LEFT|wx.TOP, 3)
		main.Add(sizer_c, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 8)

		# ── datos del día ─────────────────────────────────────────────────────
		box_d  = wx.StaticBox(p, label=_("Datos del día que quiero escuchar"))
		sizer_d = wx.StaticBoxSizer(box_d, wx.VERTICAL)
		for key, label, campoApi, tipo in OPCIONES:
			if tipo == "daily":
				cb = wx.CheckBox(p, label=label)
				cb.SetValue(prefs.get(key, True))
				self._checks[key] = cb
				sizer_d.Add(cb, 0, wx.LEFT|wx.TOP, 3)
		main.Add(sizer_d, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 8)

		# ── pronóstico ────────────────────────────────────────────────────────
		box_f  = wx.StaticBox(p, label=_("Pronóstico extendido (NVDA+Shift+W)"))
		sizer_f = wx.StaticBoxSizer(box_f, wx.HORIZONTAL)
		sizer_f.Add(wx.StaticText(p, label=_("Días a consultar (1 a 14):")), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 4)
		self.spinDays = wx.SpinCtrl(p, min=1, max=14, initial=self._cfg.get("forecast_days", 6))
		sizer_f.Add(self.spinDays, 0, wx.LEFT|wx.RIGHT, 8)
		main.Add(sizer_f, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 8)

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

	def _onClose(self, event):
		"""Garantiza que el timer se detenga siempre al cerrar el diálogo."""
		self._isClosing = True
		self._stopProgress()
		self.EndModal(wx.ID_CANCEL)

	def onCancel(self, event):
		self._isClosing = True
		self._stopProgress()
		self.EndModal(wx.ID_CANCEL)

	def EndModal(self, retCode):
		self._isClosing = True
		self._stopProgress()
		return super(ConfigDialog, self).EndModal(retCode)

	def _onProgressTick(self, event):
		if self._isClosing:
			return
		try:
			if hasattr(self, "progressBar") and self.progressBar:
				self.progressBar.SetValue((self.progressBar.GetValue() + 3) % 101)
		except (RuntimeError, Exception):
			pass

	def _stopProgress(self):
		try:
			if hasattr(self, "_progressTimer") and self._progressTimer and self._progressTimer.IsRunning():
				self._progressTimer.Stop()
		except (RuntimeError, Exception):
			pass
		try:
			if hasattr(self, "progressBar") and self.progressBar:
				self.progressBar.Hide()
		except (RuntimeError, Exception):
			pass

	# ── eventos de cambio automático ──────────────────────────────────────────

	def onCountryChange(self, event):
		idx = self.cboCountry.GetSelection()
		if idx != wx.NOT_FOUND:
			self._do_fill_regions(idx, select_first=True)

	def onRegionChange(self, event):
		idx = self.cboRegion.GetSelection()
		if idx != wx.NOT_FOUND:
			self._do_fill_cities(idx, select_first=True)

	def onCityChange(self, event):
		if self.cboCity.GetSelection() != wx.NOT_FOUND:
			self.btnSave.Enable()

	# ── países ────────────────────────────────────────────────────────────────

	def _load_countries(self):
		try:
			data      = getGeoData()
			countries = [(c[0], c[1]) for c in data]
			if not self._isClosing:
				wx.CallAfter(self._populate_countries, countries)
		except Exception as e:
			log.error("ClimaAccesible: error al cargar países: {}".format(e))
			if not self._isClosing:
				wx.CallAfter(self._stopProgress)
				wx.CallAfter(self._status, _("Error al cargar datos geográficos."))

	def _populate_countries(self, countries):
		"""Rellena la lista de países cuando termina de cargarse el archivo de lugares.

		Deja elegido el país que se guardó la última vez; si no había ninguno,
		Uruguay; y si tampoco está, el primero de la lista. Elegido el país, pide
		las regiones de ese país. Si la ventana se cerró mientras se cargaba, no
		hace nada, para no escribir en una ventana que ya no existe.
		"""
		if self._isClosing:
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

			self.cboCountry.SetFocus()
			if self.cboCity.GetSelection() != wx.NOT_FOUND:
				self.btnSave.Enable()
			self._status(_("Listo. Elige tu ubicación."))
		except (RuntimeError, Exception) as e:
			log.debugWarning("ClimaAccesible: _populate_countries ignorado: {}".format(e))

	# ── regiones ──────────────────────────────────────────────────────────────

	def _do_fill_regions(self, country_idx, select_first=False):
		"""Rellena la lista de regiones del país elegido y encadena con las ciudades.

		Con select_first en False intenta dejar puesta la región guardada; con
		True se queda con la primera. Si el país no tiene regiones, apaga las
		listas de región y ciudad y el botón Guardar, para que no se pueda
		guardar una ubicación a medias.
		"""
		if self._isClosing:
			return
		try:
			data    = getGeoData()
			country = data[country_idx]
			states  = sorted(country[2], key=lambda s: s[0])
			self._regions = [(s[0], s[2]) for s in states]
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
		except (RuntimeError, Exception) as e:
			log.debugWarning("ClimaAccesible: _do_fill_regions error: {}".format(e))

	# ── ciudades ──────────────────────────────────────────────────────────────

	def _do_fill_cities(self, region_idx, select_first=False):
		"""Rellena la lista de ciudades de la región elegida.

		Es el último eslabón de las tres listas. Con select_first en False intenta
		dejar puesta la ciudad guardada. En cuanto hay al menos una ciudad se
		enciende el botón Guardar; si no hay ninguna, se apaga.
		"""
		if self._isClosing:
			return
		try:
			_, raw_cities = self._regions[region_idx]
			self._cities = sorted(
				[(c[0], c[1], c[2]) for c in raw_cities if c[0]],
				key=lambda x: x[0]
			)
			self.cboCity.Clear()
			if self._cities:
				self.cboCity.AppendItems([name for name, _, _ in self._cities])
				self.cboCity.Enable()
				self.btnSave.Enable()

				saved_city = self._cfg.get("city", "")
				names = [c[0] for c in self._cities]
				if not select_first and saved_city in names:
					self.cboCity.SetSelection(names.index(saved_city))
				else:
					self.cboCity.SetSelection(0)
			else:
				self.cboCity.Disable()
				self.btnSave.Disable()
		except (RuntimeError, Exception) as e:
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
		if ci == wx.NOT_FOUND or not self._cities:
			self._status(_("Elige una ciudad antes de guardar."))
			return
		name, lat, lon   = self._cities[ci]
		region_name, regionResto  = self._regions[ri]
		paisResto, country_iso2  = self._countries[co]
		prefs = {key: cb.GetValue() for key, cb in self._checks.items()}
		saveJSON(_configPath(), {
			"city":          name,
			"lat":           float(lat),
			"lon":           float(lon),
			"region_name":   region_name,
			"country_iso2":  country_iso2,
			"prefs":         prefs,
			"forecast_days": self.spinDays.GetValue(),
		})
		log.info(f"ClimaAccesible: Guardando configuración - Ciudad: {name}, Coordenadas: ({lat}, {lon}), Días pronóstico: {self.spinDays.GetValue()}")
		self._status("Configuración guardada para: " + name)
		gui.messageBox(
			_("Configuración guardada.\nCiudad: {c}\nUsa NVDA+W para consultar el clima.").format(c=name),
			_("ClimaAccesible"), wx.OK | wx.ICON_INFORMATION, parent=self
		)
		self._stopProgress()
		self.EndModal(wx.ID_OK)

	def _status(self, text):
		if self._isClosing:
			return
		try:
			if hasattr(self, "lblStatus") and self.lblStatus:
				self.lblStatus.SetLabel(text)
			ui.message(text)
		except (RuntimeError, Exception):
			pass


# ── plugin principal ──────────────────────────────────────────────────────────

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	scriptCategory = _("ClimaAccesible")

	def __init__(self):
		super(GlobalPlugin, self).__init__()
		if getattr(globalVars.appArgs, "secureMode", False):
			log.warning("ClimaAccesible: NVDA en modo seguro. Se cancela la carga del complemento por seguridad.")
			raise globalPluginHandler.ActionCancelled()
		self._stopping = threading.Event()
		self._isConfigOpen = False
		self._toolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu
		self._subMenu = wx.Menu()
		self._itemConfig = self._subMenu.Append(wx.ID_ANY, _("Configuración del complemento"))
		self._itemConflicts = self._subMenu.Append(wx.ID_ANY, _("Comprobar conflictos con otros complementos..."))
		self._itemDoc = self._subMenu.Append(wx.ID_ANY, _("Documentación"))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._onMenuConfig, self._itemConfig)
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._onMenuConflicts, self._itemConflicts)
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._onMenuDoc, self._itemDoc)
		self._subMenuItem = self._toolsMenu.AppendSubMenu(
			self._subMenu, "ClimaAccesible", _("Opciones de ClimaAccesible")
		)
		threading.Thread(target=self._startupBackgroundWorker, daemon=True).start()
		log.info("ClimaAccesible: Inicializando complemento (v1.6)...")
		log.info("ClimaAccesible: Submenú registrado en Herramientas exitosamente.")

	def terminate(self):
		"""Se llama cuando NVDA cierra, reinicia o desinstala el complemento."""
		self._stopping.set()
		try:
			if hasattr(self, "_itemConfig") and self._itemConfig:
				gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, source=self._itemConfig)
			if hasattr(self, "_itemConflicts") and self._itemConflicts:
				gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, source=self._itemConflicts)
			if hasattr(self, "_itemDoc") and self._itemDoc:
				gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, source=self._itemDoc)
		except (RuntimeError, Exception) as e:
			log.debugWarning("ClimaAccesible: error al desvincular menú en terminate: {}".format(e))

		try:
			if hasattr(self, "_subMenuItem") and self._subMenuItem:
				try:
					self._toolsMenu.DestroyItem(self._subMenuItem)
				except Exception:
					self._toolsMenu.Remove(self._subMenuItem)
		except (RuntimeError, Exception) as e:
			log.warning("ClimaAccesible: error al retirar submenú en terminate: {}".format(e))

		super(GlobalPlugin, self).terminate()
		log.info("ClimaAccesible: complemento cerrado correctamente.")

	def _onMenuConfig(self, event):
		wx.CallAfter(self._openConfigDialog)

	def _onMenuDoc(self, event):
		doc_dir = os.path.normpath(os.path.join(_ADDON_DIR, "..", "doc"))
		try:
			import languageHandler
			lang = languageHandler.getLanguage().split("_")[0]
		except Exception:
			lang = "es"
		candidates = [lang, "es", "en"]
		for l in candidates:
			p = os.path.join(doc_dir, l, "readme.html")
			if os.path.exists(p):
				try:
					gui.openDocumentation(p)
					return
				except Exception as e:
					log.error(f"ClimaAccesible: No se pudo abrir la documentación con gui.openDocumentation: {e}", exc_info=True)
					# Translators: Mensaje de error cuando no se puede abrir la documentación del complemento.
					gui.messageBox(
						_("No se pudo abrir la documentación: {error}").format(error=e),
						# Translators: Título de la ventana de error al abrir la documentación.
						_("Error - ClimaAccesible"),
						wx.OK | wx.ICON_ERROR
					)
					return
		# Translators: Mensaje cuando no se encuentra el archivo de ayuda de ClimaAccesible.
		ui.message(_("No se encontró el archivo de documentación."))

	# ── scripts ───────────────────────────────────────────────────────────────

	@scriptHandler.script(
		description=_("Anuncia el clima actual de la ciudad configurada."),
		gesture="kb:nvda+w",
		speakOnDemand=True,
		category=scriptCategory,
	)
	def script_getWeather(self, gesture):
		log.info("ClimaAccesible: Atajo NVDA+W activado (lectura de clima actual).")
		cfg = loadJSON(_configPath())
		if not cfg.get("lat") or not cfg.get("lon"):
			log.warning("ClimaAccesible: Intento de consulta de clima sin ciudad configurada.")
			ui.message(_("No hay ciudad configurada. Usa NVDA+Control+W para configurar."))
			return
		log.info(f"ClimaAccesible: Consultando reporte para ciudad='{cfg.get('city')}' ({cfg.get('lat')}, {cfg.get('lon')})...")
		ui.message(_("Por favor espera, consultando el clima..."))
		t = threading.Thread(target=self._fetchWeather, args=(cfg,), daemon=True)
		t.start()

	@scriptHandler.script(
		description=_("Anuncia el pronóstico del clima para los próximos días."),
		gesture="kb:nvda+shift+w",
		speakOnDemand=True,
		category=scriptCategory,
	)
	def script_getForecast(self, gesture):
		log.info("ClimaAccesible: Atajo NVDA+Shift+W activado (lectura de pronóstico extendido).")
		cfg = loadJSON(_configPath())
		if not cfg.get("lat") or not cfg.get("lon"):
			log.warning("ClimaAccesible: Intento de consulta de pronóstico sin ciudad configurada.")
			ui.message(_("No hay ciudad configurada. Usa NVDA+Control+W para configurar."))
			return
		dias = cfg.get("forecast_days", 6)
		log.info(f"ClimaAccesible: Consultando pronóstico de {dias} días para ciudad='{cfg.get('city')}'...")
		ui.message(_("Por favor espera, consultando el pronóstico de {} días...").format(dias))
		t = threading.Thread(target=self._fetchForecast, args=(cfg,), daemon=True)
		t.start()

	@scriptHandler.script(
		description=_("Abre la ventana de configuración de ClimaAccesible."),
		gesture="kb:nvda+control+w",
		category=scriptCategory,
	)
	def script_openConfig(self, gesture):
		wx.CallAfter(self._openConfigDialog)

	def _openConfigDialog(self):
		if self._isConfigOpen:
			log.info("ClimaAccesible: Diálogo de configuración ya abierto, omitiendo.")
			return
		log.info("ClimaAccesible: Abriendo diálogo accesible de configuración...")
		self._isConfigOpen = True
		gui.mainFrame.prePopup()
		try:
			dlg = ConfigDialog(gui.mainFrame)
			dlg.ShowModal()
			dlg.Destroy()
		except Exception as e:
			log.error(f"ClimaAccesible: error en diálogo de configuración: {e}", exc_info=True)
		finally:
			gui.mainFrame.postPopup()
			self._isConfigOpen = False
			log.info("ClimaAccesible: Diálogo de configuración cerrado.")

	# ── helper interno: anunciar solo si NVDA sigue activo ────────────────────

	def _safeMessage(self, text):
		"""Llama a ui.message de forma segura solo si NVDA no está cerrándose."""
		if not self._stopping.is_set():
			log.info(f"ClimaAccesible: Anunciando al usuario: '{text}'")
			try:
				core.callLater(0, ui.message, text)
			except Exception as e:
				try:
					ui.message(text)
				except Exception as ex:
					log.error(f"ClimaAccesible: _safeMessage falló: {ex}", exc_info=True)

	def _getJsonFromApi(self, url, label="general"):
		"""Envía petición HTTP a Open-Meteo con reintento automático y decodifica JSON."""
		log.info(f"ClimaAccesible: Enviando petición HTTP ({label}) a Open-Meteo: {url}")
		req = urllib.request.Request(url, headers={"User-Agent": "ClimaAccesible/1.4"})
		raw_bytes = None
		for attempt in range(2):
			try:
				t0 = time.time()
				with urllib.request.urlopen(req, timeout=15) as r:
					raw_bytes = r.read()
					elapsed = time.time() - t0
					status_code = getattr(r, 'status', 200)
					log.info(f"ClimaAccesible: Respuesta ({label}) recibida en {elapsed:.2f}s (HTTP {status_code}, {len(raw_bytes)} bytes, intento {attempt+1}).")
					break
			except (TimeoutError, socket.timeout, urllib.error.URLError) as net_err:
				if attempt == 0 and not self._stopping.is_set():
					log.warning(f"ClimaAccesible: Reintentando petición ({label}) tras error de red: {net_err}")
					time.sleep(1.0)
					continue
				raise

		if self._stopping.is_set() or not raw_bytes:
			return None
		return json.loads(raw_bytes.decode("utf-8"))

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
		try:
			city      = cfg["city"]
			lat       = cfg["lat"]
			lon       = cfg["lon"]
			prefs_raw = cfg.get("prefs", {})
			claves_validas = {op[0] for op in OPCIONES}
			prefs = {k: prefs_raw.get(k, True) for k in claves_validas}

			url = self._urlDelClimaActual(lat, lon, prefs)
			data = self._getJsonFromApi(url, "clima actual")
			if not data or self._stopping.is_set():
				return

			c = data.get("current", {})
			d = data.get("daily",   {})
			h = data.get("hourly",  {})
			horas_time = h.get("time",                      [])
			horas_prob = h.get("precipitation_probability", [])
			horas_prec = h.get("precipitation",             [])

			def dv(key):
				v = d.get(key, [None])
				return v[0] if v else None

			hoy     = datetime.date.today().isoformat()
			momento = momentoLluvia(hoy, horas_time, horas_prob, horas_prec)

			partes = [_("En {}, el reporte del clima es el siguiente.").format(city)]
			partes += self._frasesDelClimaActual(c, prefs)
			partes += self._frasesDelResumenDeHoy(c, dv, prefs, momento)

			if len(partes) == 1:
				partes.append(_("No hay datos seleccionados. Abre la configuración con NVDA+Control+W."))

			self._safeMessage(" ".join(partes))

		except (TimeoutError, socket.timeout):
			if self._stopping.is_set():
				return
			log.error("ClimaAccesible: Tiempo de espera agotado al consultar clima.", exc_info=True)
			self._safeMessage(_("Tiempo de espera agotado al consultar el clima. Comprueba tu conexión o inténtalo nuevamente."))
		except urllib.error.HTTPError as e:
			if self._stopping.is_set():
				return
			try:
				motivo = json.loads(e.read().decode("utf-8")).get("reason", "sin detalle")
			except Exception:
				motivo = "sin detalle"
			log.error(f"ClimaAccesible: Error HTTP {e.code} al consultar clima: {motivo}", exc_info=True)
			self._safeMessage(_("Error del servidor: código {}. Motivo: {}").format(e.code, motivo))
		except urllib.error.URLError as e:
			if self._stopping.is_set():
				return
			log.error(f"ClimaAccesible: Error de conexión de red (URLError) al consultar clima: {e.reason}", exc_info=True)
			self._safeMessage(_("No se pudo conectar al servidor. Verifica tu conexión a Internet."))
		except Exception as e:
			if self._stopping.is_set():
				return
			log.error(f"ClimaAccesible: Error inesperado al consultar clima: {e}", exc_info=True)
			self._safeMessage(_("Error inesperado al consultar el clima."))

	def _urlDelClimaActual(self, lat, lon, prefs):
		"""Direccion a la que se le piden los datos del clima de ahora mismo.

		Solo se piden los datos marcados en la configuracion, para no pedirle al
		servicio lo que no se va a leer.
		"""
		current_fields = [api for k, _, api, t in OPCIONES if t == "current" and prefs.get(k, True)]
		daily_fields   = [api for k, _, api, t in OPCIONES if t == "daily"   and prefs.get(k, True)]

		params = "?latitude={lat}&longitude={lon}&wind_speed_unit=kmh&timezone=auto&forecast_days=1".format(
			lat=lat, lon=lon
		)
		if current_fields:
			params += "&current=" + ",".join(current_fields)
		if daily_fields:
			params += "&daily=" + ",".join(daily_fields)
		params += "&hourly=precipitation_probability,precipitation"

		url = "https://api.open-meteo.com/v1/forecast" + params
		return url

	def _frasesDelClimaActual(self, c, prefs):
		"""Frases sobre como esta el tiempo en este momento.

		'c' son los datos actuales y 'prefs' lo que se quiere oir. Devuelve una
		lista de frases, que puede quedar vacia si no hay nada marcado.
		"""
		partes = []
		if prefs.get("temperatura")    and "temperature_2m"       in c:
			partes.append(_("Temperatura: {} grados Celsius.").format(c["temperature_2m"]))
		if prefs.get("sensacion")      and "apparent_temperature"  in c:
			partes.append(_("Sensación térmica: {} grados.").format(c["apparent_temperature"]))
		if prefs.get("condicion")      and "weather_code"          in c:
			partes.append(_("Condición: {}.").format(codigoClima(c["weather_code"])))
		if prefs.get("es_dia")         and "is_day"                in c:
			partes.append(_("Ahora es {}.").format(_("de día") if c["is_day"] == 1 else _("de noche")))
		if prefs.get("humedad")        and "relative_humidity_2m"  in c:
			partes.append(_("Humedad: {} por ciento.").format(c["relative_humidity_2m"]))
		if prefs.get("punto_rocio")    and "dew_point_2m"          in c:
			partes.append(_("Punto de rocío: {} grados.").format(c["dew_point_2m"]))
		if prefs.get("viento_vel")     and "wind_speed_10m"        in c:
			partes.append(_("Viento a {} kilómetros por hora.").format(c["wind_speed_10m"]))
		if prefs.get("viento_dir")     and "wind_direction_10m"    in c:
			partes.append(_("Dirección del viento: {}.").format(cardinal(c["wind_direction_10m"])))
		if prefs.get("viento_rafagas") and "wind_gusts_10m"        in c:
			partes.append(_("Ráfagas de hasta {} kilómetros por hora.").format(c["wind_gusts_10m"]))
		if prefs.get("nubosidad")      and "cloud_cover"           in c:
			partes.append(_("Nubosidad: {} por ciento.").format(c["cloud_cover"]))
		if prefs.get("precipitacion")  and "precipitation"         in c:
			precip_val = float(c.get("precipitation", 0))
			if precip_val > 0:
				partes.append(_("Precipitación actual: {} milímetros.").format(precip_val))
		if prefs.get("presion")        and "surface_pressure"      in c:
			partes.append(_("Presión atmosférica: {} hectopascales.").format(c["surface_pressure"]))
		return partes

	def _frasesDelResumenDeHoy(self, c, dv, prefs, momento):
		"""Frases sobre como sera el resto del dia.

		Lo del amanecer y las horas de luz solo se dice con el cielo despejado: con
		nubes o lluvia no aporta nada y alarga el anuncio.
		"""
		partes = []
		codigo_actual   = c.get("weather_code", 99)
		cielo_despejado = codigo_actual in (0, 1)
		if cielo_despejado:
			if prefs.get("amanecer")  and dv("sunrise")           is not None:
				partes.append(_("Salida del sol: {}.").format(formatHora(dv("sunrise"))))
			if prefs.get("atardecer") and dv("sunset")            is not None:
				partes.append(_("Puesta del sol: {}.").format(formatHora(dv("sunset"))))
			if prefs.get("horas_luz") and dv("daylight_duration") is not None:
				partes.append(_("Horas de luz hoy: {}.").format(formatSegundos(dv("daylight_duration"))))
		if prefs.get("uv_max") and dv("uv_index_max") is not None:
			partes.append(_("Índice UV máximo del día: {}.").format(dv("uv_index_max")))
		if prefs.get("precip_prob_max") and dv("precipitation_probability_max") is not None:
			prob_max = int(dv("precipitation_probability_max") or 0)
			if prob_max > 0 and momento:
				partes.append(_("Probabilidad máxima de lluvia del día: {} por ciento {}.").format(prob_max, momento))
			else:
				partes.append(_("Probabilidad máxima de lluvia del día: {} por ciento.").format(prob_max))
		lluvia_total = float(dv("precipitation_sum") or 0)
		if prefs.get("precip_total") and lluvia_total > 0:
			if not prefs.get("precip_prob_max") and momento:
				partes.append(_("Precipitación total esperada del día: {} milímetros {}.").format(lluvia_total, momento))
			else:
				partes.append(_("Precipitación total esperada del día: {} milímetros.").format(dv("precipitation_sum")))
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
		try:
			city          = cfg["city"]
			lat           = cfg["lat"]
			lon           = cfg["lon"]
			forecast_days = cfg.get("forecast_days", 6)

			url = self._urlDelPronostico(lat, lon, forecast_days)
			data = self._getJsonFromApi(url, "pronóstico")
			if not data or self._stopping.is_set():
				return

			d           = data.get("daily", {})
			h           = data.get("hourly", {})
			horas_time  = h.get("time",                          [])
			horas_prob  = h.get("precipitation_probability",     [])
			horas_prec  = h.get("precipitation",                 [])
			fechas      = d.get("time",                          [])
			codigos     = d.get("weather_code",                  [])
			temp_max    = d.get("temperature_2m_max",            [])
			temp_min    = d.get("temperature_2m_min",            [])
			viento_max  = d.get("wind_speed_10m_max",            [])
			prob_precip = d.get("precipitation_probability_max", [])
			precip_sum  = d.get("precipitation_sum",             [])
			amaneceres  = d.get("sunrise",                       [])
			atardeceres = d.get("sunset",                        [])
			partes = [_("Pronóstico para {} para los próximos {} días.").format(city, len(fechas))]

			for i, fecha in enumerate(fechas):
				label     = self._nombreDeDia(fecha, i)
				codigo    = codigos[i]     if i < len(codigos)     else None
				tmax      = temp_max[i]    if i < len(temp_max)    else "?"
				tmin      = temp_min[i]    if i < len(temp_min)    else "?"
				vmax      = viento_max[i]  if i < len(viento_max)  else "?"
				prob_p    = prob_precip[i] if i < len(prob_precip) else None
				prec_s    = precip_sum[i]  if i < len(precip_sum)  else None
				amanecer  = formatHora(amaneceres[i])  if i < len(amaneceres)  else "?"
				atardecer = formatHora(atardeceres[i]) if i < len(atardeceres) else "?"
				cond      = codigoClima(codigo) if codigo is not None else "?"

				momento = momentoLluvia(fecha, horas_time, horas_prob, horas_prec)
				lluvia_info = self._fraseDeLluvia(prob_p, prec_s, momento)

				con_sol = codigo in (0, 1) if codigo is not None else False

				if con_sol:
					partes.append(
						_("{}: {}. Máxima {} grados, mínima {} grados. "
						"Viento máximo {} kilómetros por hora.{}"
						" Sol visible de {} a {}.").format(
							label.capitalize(), cond, tmax, tmin, vmax, lluvia_info, amanecer, atardecer
						)
					)
				else:
					partes.append(
						_("{}: {}. Máxima {} grados, mínima {} grados. "
						"Viento máximo {} kilómetros por hora.{}").format(
							label.capitalize(), cond, tmax, tmin, vmax, lluvia_info
						)
					)

			self._safeMessage(" ".join(partes))

		except (TimeoutError, socket.timeout):
			if self._stopping.is_set():
				return
			log.error("ClimaAccesible: Tiempo de espera agotado en pronóstico.", exc_info=True)
			self._safeMessage(_("Tiempo de espera agotado al consultar el pronóstico. Comprueba tu conexión o inténtalo nuevamente."))
		except urllib.error.HTTPError as e:
			if self._stopping.is_set():
				return
			try:
				motivo = json.loads(e.read().decode("utf-8")).get("reason", "sin detalle")
			except Exception:
				motivo = "sin detalle"
			log.error(f"ClimaAccesible: Error HTTP {e.code} en pronóstico: {motivo}", exc_info=True)
			self._safeMessage(_("Error del servidor: código {}. Motivo: {}").format(e.code, motivo))
		except urllib.error.URLError as e:
			if self._stopping.is_set():
				return
			log.error(f"ClimaAccesible: Error de conexión de red (URLError) en pronóstico: {e.reason}", exc_info=True)
			self._safeMessage(_("No se pudo conectar. Verifica tu conexión a Internet."))
		except Exception as e:
			if self._stopping.is_set():
				return
			log.error(f"ClimaAccesible: Error inesperado en pronóstico: {e}", exc_info=True)
			self._safeMessage(_("Error inesperado al consultar el pronóstico."))

	def _urlDelPronostico(self, lat, lon, forecast_days):
		"""Direccion a la que se le piden los datos del pronostico."""
		url = (
			"https://api.open-meteo.com/v1/forecast"
			"?latitude={lat}&longitude={lon}"
			"&daily=weather_code,temperature_2m_max,temperature_2m_min,"
			"precipitation_sum,precipitation_probability_max,wind_speed_10m_max,sunrise,sunset"
			"&hourly=precipitation_probability,precipitation"
			"&wind_speed_unit=kmh&timezone=auto&forecast_days={days}"
		).format(lat=lat, lon=lon, days=forecast_days)
		return url

	def _nombreDeDia(self, fecha_str, idx):
		"""Como se nombra un dia del pronostico: hoy, manana, o su fecha.

		Las listas de dias y meses se arman aqui dentro, y no fuera, porque sus
		nombres se traducen y la traduccion no esta lista hasta que NVDA arranca.
		"""
		DIAS_ES = {
			"Monday":_("lunes"), "Tuesday":_("martes"), "Wednesday":_("miércoles"),
			"Thursday":_("jueves"), "Friday":_("viernes"), "Saturday":_("sábado"), "Sunday":_("domingo"),
		}
		MESES_ES = {
			"January":_("enero"), "February":_("febrero"), "March":_("marzo"),
			"April":_("abril"), "May":_("mayo"), "June":_("junio"),
			"July":_("julio"), "August":_("agosto"), "September":_("septiembre"),
			"October":_("octubre"), "November":_("noviembre"), "December":_("diciembre"),
		}

		if idx == 0: return _("hoy")
		if idx == 1: return _("mañana")
		try:
			dt  = datetime.date.fromisoformat(fecha_str)
			dia = DIAS_ES.get(dt.strftime("%A"), dt.strftime("%A"))
			mes = MESES_ES.get(dt.strftime("%B"), dt.strftime("%B"))
			return _("{} {} de {}").format(dia, dt.day, mes)
		except Exception:
			return fecha_str

	def _fraseDeLluvia(self, prob_p, prec_s, momento):
		"""Como se cuenta la lluvia de un dia, segun lo que se sepa de ella.

		Se dice la probabilidad, los milimetros, los dos o ninguno, y se anade el
		momento del dia cuando se conoce. Devuelve cadena vacia si no hay lluvia.
		"""
		lluvia_info = ""
		try:
			prob_val = int(prob_p) if prob_p is not None else 0
		except (ValueError, TypeError):
			prob_val = 0
		try:
			prec_val = float(prec_s) if prec_s is not None else 0.0
		except (ValueError, TypeError):
			prec_val = 0.0

		if prob_val > 0 and prec_val > 0:
			if momento:
				lluvia_info = _(" Probabilidad máxima de lluvia: {} por ciento {} con {} milímetros.").format(prob_val, momento, prec_val)
			else:
				lluvia_info = _(" Probabilidad máxima de lluvia: {} por ciento con {} milímetros.").format(prob_val, prec_val)
		elif prob_val > 0:
			if momento:
				lluvia_info = _(" Probabilidad máxima de lluvia: {} por ciento {}.").format(prob_val, momento)
			else:
				lluvia_info = _(" Probabilidad máxima de lluvia: {} por ciento.").format(prob_val)
		elif prec_val > 0:
			if momento:
				lluvia_info = _(" Precipitación esperada {} de {} milímetros.").format(momento, prec_val)
			else:
				lluvia_info = _(" Precipitación esperada: {} milímetros.").format(prec_val)
		return lluvia_info


	def _startupBackgroundWorker(self):
		try:
			time.sleep(3.0)
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

		default_map = {
			"kb:nvda+w": _("Lectura del clima actual"),
			"kb:nvda+shift+w": _("Lectura del pronóstico extendido"),
			"kb:nvda+control+w": _("Ventana de configuración del clima"),
		}
		our_gestures_map = {}
		g_map = getattr(self, "_gestureMap", {}) or {}
		if g_map:
			for g_id, script_ref in g_map.items():
				norm_g = str(g_id).strip().lower().replace(" ", "")
				desc = getattr(script_ref, "description", "") or getattr(script_ref, "__doc__", "") or default_map.get(norm_g, getattr(script_ref, "__name__", str(script_ref)))
				our_gestures_map[norm_g] = desc
		else:
			our_gestures_map = default_map

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
					norm_g = str(g_id).strip().lower().replace(" ", "")
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
					norm_cmd = str(cmd_g).strip().lower().replace(" ", "")
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
		wx.CallAfter(self._checkAddonConflicts, interactive=True)

	@scriptHandler.script(
		description=_("Comprueba si existen conflictos de atajos de teclado o complementos incompatibles con ClimaAccesible."),
		category=scriptCategory,
	)
	def script_checkConflicts(self, gesture):
		self._checkAddonConflicts(interactive=True)

