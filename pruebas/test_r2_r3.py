import os
import random
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from motor import Red
from motor.estructuras import esta_ordenado, merge_sort, primer_mayor_o_igual


class TestEstructuras(unittest.TestCase):
    def test_merge_sort(self):
        datos = [random.randint(0, 50) for _ in range(500)]
        self.assertEqual(merge_sort(datos), sorted(datos))
        self.assertEqual(merge_sort([]), [])

    def test_esta_ordenado(self):
        self.assertTrue(esta_ordenado([]))
        self.assertTrue(esta_ordenado(["A", "B", "B", "C"]))
        self.assertFalse(esta_ordenado(["A", "C", "B"]))

    def test_primer_mayor_o_igual(self):
        a = ["B", "D", "F"]
        self.assertEqual(primer_mayor_o_igual(a, "A"), 0)
        self.assertEqual(primer_mayor_o_igual(a, "D"), 1)
        self.assertEqual(primer_mayor_o_igual(a, "E"), 2)
        self.assertEqual(primer_mayor_o_igual(a, "Z"), 3)


class TestR2R3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.red = Red(os.path.join(RAIZ, "datos"))

    def test_autocompletar(self):
        self.assertEqual(self.red.autocompletar("CAL", 3), ["CALLE 100", "CALLE 106", "CALLE 127"])
        self.assertEqual(self.red.autocompletar("PORTAL", 20)[0], "PORTAL 20 DE JULIO")
        self.assertEqual(len(self.red.autocompletar("PORTAL", 20)), 9)

    def test_autocompletar_bordes(self):
        self.assertEqual(self.red.autocompletar("XYZ", 5), [])
        self.assertEqual(self.red.autocompletar("CAL", 0), [])
        self.assertEqual(self.red.autocompletar("CALLE 26", 5), ["CALLE 26"])
        self.assertEqual(self.red.autocompletar("", 2), ["21 ANGELES", "AGUAS"])

    def test_rango(self):
        r = self.red.rango("CALLE 26", "CALLE 80")
        self.assertEqual(r[0], "CALLE 26")
        self.assertEqual(r[-1], "CALLE 76")
        self.assertEqual(r, sorted(r))

    def test_rango_bordes(self):
        self.assertEqual(self.red.rango("CALLE 80", "CALLE 26"), [])
        self.assertEqual(self.red.rango("CALLE 26", "CALLE 26"), ["CALLE 26"])
        self.assertEqual(len(self.red.rango("", "ZZZ")), 147)

    def test_csv_desordenado(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "estaciones.csv"), "w", encoding="utf-8") as f:
            f.write("nombre\nCHARLIE\nALFA\nDELTA\nBRAVO\nALFA\n")
        with open(os.path.join(d, "rutas.csv"), "w", encoding="utf-8") as f:
            f.write("ruta,orden,estacion\n")
        with open(os.path.join(d, "horarios.csv"), "w", encoding="utf-8") as f:
            f.write("ruta,estacion,hora\n")
        red = Red(d)
        self.assertEqual(red.rango("A", "Z"), ["ALFA", "BRAVO", "CHARLIE", "DELTA"])


if __name__ == "__main__":
    unittest.main()
