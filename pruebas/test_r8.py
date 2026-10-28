import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from motor import Red


class TestR8Estructura(unittest.TestCase):
    def setUp(self):
        self.red = Red(os.path.join(RAIZ, "datos"))

    def _est(self, nombre):
        return self.red._estaciones.obtener(nombre)

    def test_cerrada_no_sale_en_consultas(self):
        self.red._cerrar_estacion(self._est("CALLE 100"))
        self.assertEqual(self.red.estado("CALLE 100"), "cerrada")
        self.assertEqual(self.red.autocompletar("CALLE 1", 2), ["CALLE 106", "CALLE 127"])
        self.assertEqual(self.red.rango("CALLE 100", "CALLE 106"), ["CALLE 106"])

    def test_reabrir_vuelve_a_su_lugar(self):
        self.red._cerrar_estacion(self._est("CALLE 100"))
        self.red._abrir_estacion(self._est("CALLE 100"))
        self.assertEqual(self.red.autocompletar("CALLE 1", 2), ["CALLE 100", "CALLE 106"])
        self.assertEqual(len(self.red.rango("", "ZZZ")), 147)

    def test_extremos_y_repetidos(self):
        for nombre in ["21 ANGELES", "ZONA INDUSTRIAL"]:
            self.red._cerrar_estacion(self._est(nombre))
            self.red._cerrar_estacion(self._est(nombre))
        todas = self.red.rango("", "ZZZ")
        self.assertEqual(len(todas), 145)
        self.assertEqual(todas[0], "AGUAS")
        self.red._abrir_estacion(self._est("ZONA INDUSTRIAL"))
        self.red._abrir_estacion(self._est("ZONA INDUSTRIAL"))
        self.assertEqual(self.red.rango("", "ZZZ")[-1], "ZONA INDUSTRIAL")
        self.assertEqual(len(self.red.rango("", "ZZZ")), 146)


if __name__ == "__main__":
    unittest.main()
