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


class TestR4ConCambios(unittest.TestCase):
    def setUp(self):
        self.red = Red(os.path.join(RAIZ, "datos"))
        self.hora = self.red.proximo_bus("UNIVERSIDADES", "1-1", "07:00")

    def test_estacion_cerrada(self):
        self.assertIsNotNone(self.hora)
        self.red.cerrar("UNIVERSIDADES")
        self.assertIsNone(self.red.proximo_bus("UNIVERSIDADES", "1-1", "07:00"))
        self.red.reabrir("UNIVERSIDADES")
        self.assertEqual(self.red.proximo_bus("UNIVERSIDADES", "1-1", "07:00"), self.hora)

    def test_parada_quitada_y_deshacer(self):
        self.red.quitar_parada("1-1", "UNIVERSIDADES")
        self.assertIsNone(self.red.proximo_bus("UNIVERSIDADES", "1-1", "07:00"))
        self.red.deshacer()
        self.assertEqual(self.red.proximo_bus("UNIVERSIDADES", "1-1", "07:00"), self.hora)

    def test_cierre_deshecho(self):
        self.red.cerrar("UNIVERSIDADES")
        self.red.deshacer()
        self.assertEqual(self.red.proximo_bus("UNIVERSIDADES", "1-1", "07:00"), self.hora)


if __name__ == "__main__":
    unittest.main()


class TestHorasExtendidas(unittest.TestCase):
    """Horas del GTFS como 25:10 (README, "Horas"): se ordenan después de 23:59."""

    def test_proximo_bus_despues_de_medianoche(self):
        import tempfile
        with tempfile.TemporaryDirectory() as carpeta:
            with open(os.path.join(carpeta, "estaciones.csv"), "w", encoding="utf-8") as f:
                f.write("nombre\nA\nB\n")
            with open(os.path.join(carpeta, "rutas.csv"), "w", encoding="utf-8") as f:
                f.write("ruta,orden,estacion\nR,1,A\nR,2,B\n")
            with open(os.path.join(carpeta, "horarios.csv"), "w", encoding="utf-8") as f:
                f.write("ruta,estacion,hora\nR,A,23:40\nR,A,25:10\nR,A,05:00\n")
            red = Red(carpeta)
        self.assertEqual(red.proximo_bus("A", "R", "23:50"), "25:10")
        self.assertEqual(red.proximo_bus("A", "R", "23:30"), "23:40")
        self.assertIsNone(red.proximo_bus("A", "R", "25:11"))
