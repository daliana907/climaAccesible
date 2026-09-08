# -*- coding: utf-8 -*-
"""Pruebas de la lógica de ClimaAccesible que no necesita NVDA abierto.

Se prueban las funciones que convierten datos del servicio meteorológico en
frases: dirección del viento, condición del cielo, duraciones y momentos de
lluvia. Son puras: misma entrada, misma salida.
"""
import os
import sys
import unittest

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


class Duraciones(unittest.TestCase):
    def test_horas_y_minutos(self):
        self.assertEqual(clima.formatSegundos(3660), "1 horas y 1 minutos")

    def test_solo_horas(self):
        self.assertEqual(clima.formatSegundos(7200), "2 horas")

    def test_solo_minutos(self):
        self.assertEqual(clima.formatSegundos(600), "10 minutos")

    def test_valor_no_numerico_no_revienta(self):
        self.assertIsInstance(clima.formatSegundos("hola"), str)


class MomentosDeLluvia(unittest.TestCase):
    """Convierte las horas con lluvia en una frase como 'por la mañana'."""

    def _horas(self, *horas):
        tiempos = [f"2026-09-08T{h:02d}:00" for h in range(24)]
        probs = [90 if h in horas else 0 for h in range(24)]
        precs = [1 if h in horas else 0 for h in range(24)]
        return "2026-09-08", tiempos, probs, precs

    def test_sin_lluvia_no_dice_nada(self):
        self.assertEqual(clima.momentoLluvia(*self._horas()), "")

    def test_un_solo_periodo(self):
        texto = clima.momentoLluvia(*self._horas(9, 10, 11))
        self.assertIn("mañana", texto)

    def test_todo_el_dia(self):
        texto = clima.momentoLluvia(*self._horas(3, 9, 15, 21))
        self.assertEqual(texto, "durante todo el día")

    def test_devuelve_siempre_texto(self):
        for horas in ([], [0], [23], list(range(24)), [5, 17]):
            self.assertIsInstance(clima.momentoLluvia(*self._horas(*horas)), str)

    def test_datos_incompletos_no_revientan(self):
        self.assertIsInstance(clima.momentoLluvia("2026-09-08", [], [], []), str)


class FraseDeLluviaDeUnDia(unittest.TestCase):
    """Como se cuenta la lluvia de un dia del pronostico.

    Hay cuatro casos (probabilidad, milimetros, los dos, ninguno) y cada uno
    cambia segun se conozca o no el momento del dia. Estaba metido dentro de un
    bucle de cincuenta lineas donde no se podia comprobar por separado.
    """

    def frase(self, prob, milimetros, momento=""):
        return clima.GlobalPlugin._fraseDeLluvia(None, prob, milimetros, momento)

    def test_sin_lluvia_no_dice_nada(self):
        for prob, mm in ((None, None), (0, 0), ("0", "0"), (0, None), (None, 0)):
            with self.subTest(prob=prob, mm=mm):
                self.assertEqual(self.frase(prob, mm), "")

    def test_solo_probabilidad(self):
        texto = self.frase(60, 0)
        self.assertIn("60", texto)
        self.assertNotIn("milímetros", texto)

    def test_solo_milimetros(self):
        texto = self.frase(0, 3.5)
        self.assertIn("3.5", texto)

    def test_probabilidad_y_milimetros(self):
        texto = self.frase(80, 12)
        self.assertIn("80", texto)
        self.assertIn("12", texto)

    def test_el_momento_del_dia_se_anade_cuando_se_conoce(self):
        con = self.frase(60, 0, "por la tarde")
        sin = self.frase(60, 0, "")
        self.assertIn("por la tarde", con)
        self.assertNotIn("por la tarde", sin)

    def test_un_dato_estropeado_no_revienta(self):
        """El servicio puede devolver texto donde deberia haber un numero."""
        for prob, mm in (("abc", None), (None, "x"), ("", ""), ([], {})):
            with self.subTest(prob=prob, mm=mm):
                self.assertIsInstance(self.frase(prob, mm), str)


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
