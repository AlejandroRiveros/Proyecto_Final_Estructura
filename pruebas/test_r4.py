import csv
import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from motor import Red


def horas_de(ruta, estacion):
    salida = set()
    with open(os.path.join(RAIZ, "datos", "horarios.csv"), encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if fila["ruta"] == ruta and fila["estacion"] == estacion:
                salida.add(fila["hora"])
    return sorted(salida)


class TestR4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.red = Red(os.path.join(RAIZ, "datos"))
        cls.horas = horas_de("1-1", "UNIVERSIDADES")

    def test_contra_fuerza_bruta(self):
        for hora in ["00:00", "05:30", "07:40", "12:00", "18:15", "23:59"]:
            esperado = None
            for h in self.horas:
                if h >= hora:
                    esperado = h
                    break
            self.assertEqual(self.red.proximo_bus("UNIVERSIDADES", "1-1", hora), esperado, hora)

    def test_hora_exacta(self):
        h = self.horas[3]
        self.assertEqual(self.red.proximo_bus("UNIVERSIDADES", "1-1", h), h)

    def test_sin_mas_buses(self):
        self.assertIsNone(self.red.proximo_bus("UNIVERSIDADES", "1-1", "23:59" if self.horas[-1] < "23:59" else "99:99"))

    def test_par_inexistente(self):
        self.assertIsNone(self.red.proximo_bus("UNIVERSIDADES", "NO EXISTE", "07:00"))
        self.assertIsNone(self.red.proximo_bus("NO EXISTE", "1-1", "07:00"))

    def test_sin_repetidas_y_ordenadas(self):
        guardadas = self.red._horarios.obtener("1-1").obtener("UNIVERSIDADES")
        self.assertEqual(guardadas, self.horas)


if __name__ == "__main__":
    unittest.main()
