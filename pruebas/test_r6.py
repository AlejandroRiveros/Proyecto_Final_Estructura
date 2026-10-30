import csv
import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from motor import Red


def _conteo_csv():
    conteo = {}
    with open(os.path.join(RAIZ, "datos", "horarios.csv"), encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            clave = (fila["ruta"], fila["estacion"])
            conteo[clave] = conteo.get(clave, 0) + 1
    return conteo


CONTEO = _conteo_csv()


def ranking_bruto(red):
    """Ranking calculado a lo bruto, solo para comparar en las pruebas (aquí sí se permite dict)."""
    conteo = CONTEO
    buses = {}
    for nombre_ruta in red._rutas.claves():
        for est in red.recorrido(nombre_ruta):
            buses[est] = buses.get(est, 0) + conteo.get((nombre_ruta, est), 0)
    abiertas = [n for n in red.rango("", "￿")]
    return sorted(abiertas, key=lambda n: (-buses.get(n, 0), n))


class TestR6(unittest.TestCase):
    def setUp(self):
        self.red = Red(os.path.join(RAIZ, "datos"))

    def assertInvariante(self):
        r = self.red._ranking
        for i in range(len(r)):
            self.assertEqual(r[i].pos_ranking, i)
            if i > 0:
                self.assertTrue(r[i - 1].buses > r[i].buses or
                                (r[i - 1].buses == r[i].buses and r[i - 1].nombre < r[i].nombre))
        self.assertEqual(self.red.ranking(len(r) + 5), ranking_bruto(self.red))

    def test_contra_fuerza_bruta(self):
        self.assertEqual(self.red.ranking(10), ranking_bruto(self.red)[:10])
        self.assertInvariante()

    def test_bordes(self):
        self.assertEqual(self.red.ranking(0), [])
        self.assertEqual(len(self.red.ranking(1000)), 147)

    def test_cerrar_y_reabrir(self):
        primera = self.red.ranking(1)[0]
        self.red.cerrar(primera)
        self.assertNotEqual(self.red.ranking(1)[0], primera)
        self.assertInvariante()
        self.red.reabrir(primera)
        self.assertEqual(self.red.ranking(1)[0], primera)
        self.assertInvariante()

    def test_editar_rutas_y_deshacer(self):
        ruta = "1-1"
        paradas = self.red.recorrido(ruta)
        antes = self.red.ranking(147)
        self.red.quitar_parada(ruta, paradas[1])
        self.assertInvariante()
        self.red.agregar_parada(ruta, "CALLE 26", paradas[0])  # sin horarios en la 1-1: suma 0
        self.assertInvariante()
        self.red.deshacer()
        self.red.deshacer()
        self.assertEqual(self.red.ranking(147), antes)
        self.red.rehacer()
        self.assertInvariante()

    def test_cerrada_editada_no_entra(self):
        ruta = "1-1"
        paradas = self.red.recorrido(ruta)
        self.red.cerrar(paradas[1])
        self.red.quitar_parada(ruta, paradas[1])
        self.assertInvariante()
        self.red.reabrir(paradas[1])
        self.assertInvariante()


if __name__ == "__main__":
    unittest.main()
