"""El motor con los CSV que produce nuestro conversor (conversion/generados/).

La app y las demás pruebas usan datos/ (los CSV del profesor). Aquí se carga
Red("conversion/generados") y se comprueban consultas, viajes y ranking:
- lo que depende solo de estaciones y rutas (idénticas a las del profesor)
  debe dar lo mismo que con datos/;
- lo que depende de horarios (R4, R6) se compara con un cálculo a lo bruto
  sobre conversion/generados/horarios.csv, porque ahí hay 36 filas de más.
Fuera de motor/ se permiten dict y sorted.
"""

import csv
import os
import random
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from motor import Red

GENERADOS = os.path.join(RAIZ, "conversion", "generados")
PROFESOR = os.path.join(RAIZ, "datos")


def _horarios(carpeta):
    filas = []
    with open(os.path.join(carpeta, "horarios.csv"), encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            filas.append((fila["ruta"], fila["estacion"], fila["hora"]))
    return filas


@unittest.skipUnless(os.path.isdir(GENERADOS), "falta conversion/generados")
class TestGenerados(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gen = Red(GENERADOS)
        cls.prof = Red(PROFESOR)
        cls.estaciones = cls.gen.rango("", "￿")
        cls.rutas = sorted(cls.gen._rutas.claves())
        cls.filas = _horarios(GENERADOS)

    def test_estaciones_y_rutas_iguales_a_las_del_profesor(self):
        self.assertEqual(self.estaciones, self.prof.rango("", "￿"))
        self.assertEqual(len(self.estaciones), 147)
        self.assertEqual(self.rutas, sorted(self.prof._rutas.claves()))
        for r in self.rutas:
            self.assertEqual(self.gen.recorrido(r), self.prof.recorrido(r), r)
            self.assertEqual(self.gen.recorrido(r, al_reves=True), self.prof.recorrido(r, al_reves=True), r)
        for e in self.estaciones:
            self.assertEqual(self.gen.estado(e), "abierta")
        for p in ["A", "CALLE", "PORTAL", "SU", "ZZ"]:
            self.assertEqual(self.gen.autocompletar(p, 10), self.prof.autocompletar(p, 10))

    def test_viajes_iguales_a_los_del_profesor(self):
        # R5 depende solo de rutas y estaciones, que son idénticas.
        azar = random.Random(5)
        for _ in range(400):
            a, b = azar.sample(self.estaciones, 2)
            self.assertEqual(self.gen.viaje(a, b), self.prof.viaje(a, b), (a, b))

    def test_proximo_bus_contra_calculo_bruto(self):
        horas = {}
        for r, e, h in self.filas:
            horas.setdefault((r, e), set()).add(h)
        azar = random.Random(4)
        pares = sorted(horas)
        for _ in range(3000):
            r, e = azar.choice(pares)
            h = "%02d:%02d" % (azar.randrange(24), azar.randrange(60))
            despues = sorted(x for x in horas[(r, e)] if x >= h)
            esperado = despues[0] if despues else None
            if e not in self.gen.recorrido(r):
                esperado = None
            self.assertEqual(self.gen.proximo_bus(e, r, h), esperado, (e, r, h))

    def test_ranking_contra_calculo_bruto(self):
        conteo = {}
        for r, e, _ in self.filas:
            conteo[(r, e)] = conteo.get((r, e), 0) + 1
        buses = {}
        for r in self.rutas:
            for e in self.gen.recorrido(r):
                buses[e] = buses.get(e, 0) + conteo.get((r, e), 0)
        esperado = sorted(self.estaciones, key=lambda n: (-buses.get(n, 0), n))
        self.assertEqual(self.gen.ranking(len(esperado)), esperado)


if __name__ == "__main__":
    unittest.main()
