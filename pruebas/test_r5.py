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


def bruto_transbordos(red, origen, destino):
    """(tramos, paradas) mínimos con cualquier número de transbordos.
    Dijkstra con heapq sobre estaciones (fuera del motor se permite);
    cada salto es un tramo completo, con costo (1, paradas del tramo)."""
    import heapq
    if origen == destino or red.estado(origen) != "abierta" or red.estado(destino) != "abierta":
        return None
    rutas = [red.recorrido(n) for n in red._rutas.claves()]
    mejor = {origen: (0, 0)}
    cola = [(0, 0, origen)]
    while cola:
        t, p, x = heapq.heappop(cola)
        if (t, p) > mejor[x]:
            continue
        if x == destino:
            return (t, p)
        for paradas in rutas:
            if x not in paradas:
                continue
            i = paradas.index(x)
            for j in range(i + 1, len(paradas)):
                y = paradas[j]
                if red.estado(y) != "abierta":
                    continue
                c = (t + 1, p + j - i)
                if y not in mejor or c < mejor[y]:
                    mejor[y] = c
                    heapq.heappush(cola, (c[0], c[1], y))
    return None


class TestViajeConTransbordos(unittest.TestCase):
    """Búsqueda con más transbordos (BFS por tramos), apoyo de la app."""

    def revisar(self, red, origen, destino, tramos):
        self.assertEqual(tramos[0][1], origen)
        self.assertEqual(tramos[-1][2], destino)
        for (r1, _, baja), (r2, sube, _) in zip(tramos, tramos[1:]):
            self.assertEqual(baja, sube)
            self.assertNotEqual(r1, r2)
            self.assertEqual(red.estado(sube), "abierta")
        for ruta, sube, baja in tramos:
            p = red.recorrido(ruta)
            self.assertLess(p.index(sube), p.index(baja))

    def test_tres_tramos_en_la_red_real(self):
        red = Red(os.path.join(RAIZ, "datos"))
        tramos = red.viaje_con_transbordos("AV. AMERICAS - AV. BOYACA", "BOSA")
        self.assertEqual(len(tramos), 3)
        self.revisar(red, "AV. AMERICAS - AV. BOYACA", "BOSA", tramos)

    def test_menos_tramos_antes_que_menos_paradas(self):
        # Directo de 6 paradas contra 2 tramos de 2 paradas: gana el directo.
        red = red_de({"L": ["A", "B", "C", "D", "E", "F", "Z"],
                      "X": ["A", "M"], "Y": ["M", "Z"]})
        self.assertEqual(red.viaje_con_transbordos("A", "Z"), [("L", "A", "Z")])

    def test_desempate_por_paradas_en_el_mismo_nivel(self):
        # B y C están en la misma ruta S desde A, así que B entra a la cola
        # antes. Q se descubre primero desde B (6 paradas) y luego se mejora
        # desde C (4) en el mismo nivel: el viaje debe ir por C.
        red = red_de({"S": ["A", "B", "X", "C"], "R2": ["B", "P", "P2", "P3", "P4", "Q"],
                      "S2": ["C", "Q"], "R3": ["Q", "Z"]})
        tramos = red.viaje_con_transbordos("A", "Z")
        self.assertEqual(tramos, [("S", "A", "C"), ("S2", "C", "Q"), ("R3", "Q", "Z")])
        self.assertEqual(paradas_de(red, tramos), 5)
        self.revisar(red, "A", "Z", tramos)

    def test_cerradas_y_bordes(self):
        red = red_de({"R1": ["A", "B"], "R2": ["B", "C"], "R3": ["C", "D"]})
        self.assertEqual(len(red.viaje_con_transbordos("A", "D")), 3)
        red.cerrar("C")  # no se puede transbordar en C
        self.assertIsNone(red.viaje_con_transbordos("A", "D"))
        red.deshacer()
        self.assertIsNone(red.viaje_con_transbordos("A", "A"))
        self.assertIsNone(red.viaje_con_transbordos("D", "A"))  # sentido único
        self.assertIsNone(red.viaje_con_transbordos("A", "NO EXISTE"))

    def test_resuelve_lo_que_r5_no(self):
        red = Red(os.path.join(RAIZ, "datos"))
        nombres = red.rango("", "\uffff")
        sin_r5 = 0
        for o in nombres:
            for d in nombres:
                if o != d and red.viaje(o, d) is None:
                    sin_r5 += 1
                    tramos = red.viaje_con_transbordos(o, d)
                    self.assertIsNotNone(tramos, (o, d))
                    self.revisar(red, o, d, tramos)
        self.assertEqual(sin_r5, 518)

    def test_contra_dijkstra(self):
        red = Red(os.path.join(RAIZ, "datos"))
        nombres = red.rango("", "\uffff")
        azar = random.Random(11)
        for paso in range(200):
            if paso == 100:
                for e in azar.sample(nombres, 15):
                    red.cerrar(e)
            o, d = azar.sample(nombres, 2)
            tramos = red.viaje_con_transbordos(o, d)
            esperado = bruto_transbordos(red, o, d)
            if esperado is None:
                self.assertIsNone(tramos, (o, d))
            else:
                self.revisar(red, o, d, tramos)
                self.assertEqual((len(tramos), paradas_de(red, tramos)), esperado, (o, d))


if __name__ == "__main__":
    unittest.main()
