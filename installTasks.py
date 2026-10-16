# -*- coding: utf-8 -*-
# Accessible Weather (ClimaAccesible) for NVDA - Install Tasks
# Inspired by Weather Plus (Adriano Barbieri and contributors).
# Maintained by Daliana, released under the GNU General Public License version 2 (GPLv2).

import os
import globalVars
from logHandler import log

def onInstall():
	"""Se ejecuta al instalar el complemento."""
	log.info("ClimaAccesible: instalación completada.")

def onUninstall():
	"""
	Se ejecuta al desinstalar el complemento.
	Elimina el archivo de configuración del perfil de NVDA.
	"""
	try:
		config_path = getattr(getattr(globalVars, "appArgs", None), "configPath", None)
		if config_path:
			for fname in ("climaAccesible.json", "climaAccesible.json.tmp", "climaAccesible.json.corrupto.bak"):
				p = os.path.join(config_path, fname)
				if os.path.exists(p):
					try: os.remove(p)
					except OSError as _e:
						log.debugWarning("ClimaAccesible: no se pudo borrar {}: {}".format(p, _e), exc_info=True)
		log.info("ClimaAccesible: configuración y temporales eliminados al desinstalar.")
	except Exception as e:
		log.warning("ClimaAccesible: no se pudo eliminar la configuración: {}".format(e))
