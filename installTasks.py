# -*- coding: utf-8 -*-
# Accessible Weather (ClimaAccesible) for NVDA - Install Tasks
# Copyright 2026 Daliana, released under the GNU General Public License version 2 (GPLv2).

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
		config_file = os.path.join(globalVars.appArgs.configPath, "climaAccesible.json")
		if os.path.exists(config_file):
			os.remove(config_file)
			log.info("ClimaAccesible: configuración eliminada al desinstalar.")
	except Exception as e:
		log.warning("ClimaAccesible: no se pudo eliminar la configuración: {}".format(e))
