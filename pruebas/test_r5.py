import os
import random
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from motor import Red


def red_de(rutas):
    """Red sintética: rutas = {"R1": ["A", "B", ...], ...}."""
    d = tempfile.mkdtemp()
    estaciones = sorted({e for paradas in rutas.values() for e in paradas})
    with open(os.path.join(d, "estaciones.csv"), "w", encoding="utf-8") as f:
        f.write("nombre\n" + "\n".join(estaciones) + "\n")
    with open(os.path.join(d, "rutas.csv"), "w", encoding="utf-8") as f:
        f.write("ruta,orden,estacion\n")
        for ruta, paradas in rutas.items():
            for i, e in enumerate(paradas):
                f.write("%s,%d,%s\n" % (ruta, i + 1, e))
    with open(os.path.join(d, "horarios.csv"), "w", encoding="utf-8") as f:
        f.write("ruta,estacion,hora\n")
    return Red(d)


def bruto(red, origen, destino):
    """Todas las combinaciones (opción A), solo para comparar en las pruebas."""
    if origen == destino or red.estado(origen) != "abierta" or red.estado(destino) != "abierta":
        return None
    candidatos = []
    rutas = {n: red.recorrido(n) for n in red._rutas.claves()}
    for r1, p1 in rutas.items():
        if origen not in p1:
            continue
        i = p1.index(origen)
        for j in range(i + 1, len(p1)):
            if p1[j] == destino:
                candidatos.append((j - i, 0, r1, "", ""))
            t = p1[j]
            if t == destino or red.estado(t) != "abierta":
                continue
            for r2, p2 in rutas.items():
                if r2 == r1 or t not in p2 or destino not in p2:
                    continue
                a, b = p2.index(t), p2.index(destino)
                if a < b:
                    candidatos.append((j - i + b - a, 1, r1, t, r2))
    if not candidatos:
        return None
    return min(candidatos)[0]


def paradas_de(red, tramos):
    total = 0
    for ruta, sube, baja in tramos:
        p = red.recorrido(ruta)
        total += p.index(baja) - p.index(sube)
    return total


class TestR5Casos(unittest.TestCase):
    def test_directo_mas_largo_que_transbordo(self):
        red = red_de({
            "LENTA": ["O", "X1", "X2", "X3", "X4", "X5", "D"],
            "R1": ["O", "T"],
            "R2": ["T", "D"],
        })
        self.assertEqual(red.viaje("O", "D"), [("R1", "O", "T"), ("R2", "T", "D")])

    def test_empate_prefiere_directo(self):
        red = red_de({"DIR": ["O", "M", "D"], "R1": ["O", "T"], "R2": ["T", "D"]})
        self.assertEqual(red.viaje("O", "D"), [("DIR", "O", "D")])

    def test_mejor_llegada_por_estacion(self):
        # Dos rutas llegan a T: LARGA en 4 paradas y CORTA en 1. Debe usar CORTA.
        red = red_de({
            "CORTA": ["O", "T"],
            "LARGA": ["O", "Y1", "Y2", "Y3", "T"],
            "FIN": ["T", "D"],
        })
        self.assertEqual(red.viaje("O", "D"), [("CORTA", "O", "T"), ("FIN", "T", "D")])
        # Al revés en el orden de carga no debe cambiar el resultado.
        red2 = red_de({
            "LARGA": ["O", "Y1", "Y2", "Y3", "T"],
            "CORTA": ["O", "T"],
            "FIN": ["T", "D"],
        })
        self.assertEqual(red2.viaje("O", "D"), [("CORTA", "O", "T"), ("FIN", "T", "D")])

    def test_sentido_unico(self):
        red = red_de({"R": ["A", "B", "C"]})
        self.assertEqual(red.viaje("A", "C"), [("R", "A", "C")])
        self.assertIsNone(red.viaje("C", "A"))

    def test_cierres(self):
        red = red_de({"R1": ["O", "T", "M"], "R2": ["T", "D"], "R3": ["M", "D"]})
        self.assertEqual(red.viaje("O", "D"), [("R1", "O", "T"), ("R2", "T", "D")])
        red.cerrar("T")
        # T cerrada no sirve de transbordo, pero no corta la R1: se cambia en M.
        self.assertEqual(red.viaje("O", "D"), [("R1", "O", "M"), ("R3", "M", "D")])
        red.cerrar("D")
        self.assertIsNone(red.viaje("O", "D"))
        red.deshacer()
        red.deshacer()
        self.assertEqual(red.viaje("O", "D"), [("R1", "O", "T"), ("R2", "T", "D")])

    def test_cerrada_intermedia_no_corta_directo(self):
        red = red_de({"R": ["A", "B", "C"]})
        red.cerrar("B")
        self.assertEqual(red.viaje("A", "C"), [("R", "A", "C")])

    def test_bordes(self):
        red = red_de({"R": ["A", "B"]})
        self.assertIsNone(red.viaje("A", "A"))
        self.assertIsNone(red.viaje("A", "NO EXISTE"))
        red.cerrar("A")
        self.assertIsNone(red.viaje("A", "B"))

    def test_indice_sigue_ediciones_y_deshacer(self):
        red = red_de({"R1": ["O", "T"], "R2": ["X", "D"]})
        self.assertIsNone(red.viaje("O", "D"))
        red.agregar_parada("R2", "T", "X")
        self.assertEqual(red.viaje("O", "D"), [("R1", "O", "T"), ("R2", "T", "D")])
        red.deshacer()
        self.assertIsNone(red.viaje("O", "D"))
        red.rehacer()
        red.quitar_parada("R2", "T")
        self.assertIsNone(red.viaje("O", "D"))


class TestR5ContraFuerzaBruta(unittest.TestCase):
    def test_red_real(self):
        red = Red(os.path.join(RAIZ, "datos"))
        nombres = red.rango("", "￿")
        azar = random.Random(7)
        for paso in range(250):
            if paso == 125:
                for e in azar.sample(nombres, 15):
                    red.cerrar(e)
            o, d = azar.sample(nombres, 2)
            tramos = red.viaje(o, d)
            esperado = bruto(red, o, d)
            if esperado is None:
                self.assertIsNone(tramos, (o, d))
            else:
                self.assertIsNotNone(tramos, (o, d))
                self.assertEqual(paradas_de(red, tramos), esperado, (o, d))
                self.assertEqual(tramos[0][1], o)
                self.assertEqual(tramos[-1][2], d)


if __name__ == "__main__":
    unittest.main()
