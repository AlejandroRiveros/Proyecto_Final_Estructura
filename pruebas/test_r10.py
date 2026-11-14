import os
import random
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from motor import simular_fila


def fila_a_lo_bruto(llegadas, frecuencia, capacidad):
    """Recorre los buses uno por uno (sin saltos). Fuera de motor/ vale sorted.

    Devuelve el segundo de salida del bus de cada persona, en el orden de la lista.
    """
    orden = sorted(range(len(llegadas)), key=lambda i: (llegadas[i], i))
    salidas = [None] * len(llegadas)
    bus = frecuencia
    j = 0
    while j < len(orden):
        suben = 0
        while j < len(orden) and llegadas[orden[j]] <= bus and suben < capacidad:
            salidas[orden[j]] = bus
            j += 1
            suben += 1
        bus += frecuencia
    return salidas


class TestR10(unittest.TestCase):
    def test_ejemplo_del_enunciado(self):
        # Las dos personas del segundo 5 suben al bus de los 60; la de 30 y la
        # de 70, al de los 120. El resultado va en el orden de la lista.
        self.assertEqual(simular_fila([30, 5, 5, 70], 60, 2), [120, 60, 60, 120])

    def test_primer_bus_en_frecuencia(self):
        # No hay bus en el segundo 0: el primero sale en `frecuencia`.
        self.assertEqual(simular_fila([0], 60, 5), [60])

    def test_fifo_y_empates_en_orden_de_la_lista(self):
        # Llegan tres en el segundo 10 y cabe uno por bus: suben en el orden de la lista.
        self.assertEqual(simular_fila([10, 10, 10], 20, 1), [20, 40, 60])

    def test_sin_llegadas(self):
        self.assertEqual(simular_fila([], 5, 10), [])

    def test_parametros_invalidos(self):
        self.assertIsNone(simular_fila([0, 1], 0, 3))
        self.assertIsNone(simular_fila([0, 1], 5, 0))

    def test_llega_justo_cuando_sale(self):
        self.assertEqual(simular_fila([60, 60], 60, 2), [60, 60])

    def test_cupo_lleno_espera_otro_bus(self):
        self.assertEqual(simular_fila([0, 0, 0], 10, 2), [10, 10, 20])

    def test_salta_buses_vacios(self):
        self.assertEqual(simular_fila([1000003], 10, 1), [1000010])

    def test_desordenadas_y_no_modifica_la_entrada(self):
        llegadas = [70, 5, 30, 5]
        self.assertEqual(simular_fila(llegadas, 60, 2), [120, 60, 120, 60])
        self.assertEqual(llegadas, [70, 5, 30, 5])

    def test_contra_calculo_bruto(self):
        azar = random.Random(10)
        for _ in range(300):
            n = azar.randrange(0, 60)
            llegadas = [azar.randrange(0, 300) for _ in range(n)]
            f = azar.randrange(1, 40)
            c = azar.randrange(1, 6)
            self.assertEqual(simular_fila(llegadas, f, c), fila_a_lo_bruto(llegadas, f, c),
                             (llegadas, f, c))

    def test_cientos_de_miles(self):
        # 300.000 personas, una por segundo... en desorden.
        azar = random.Random(3)
        llegadas = [azar.randrange(0, 3600) for _ in range(300000)]
        salidas = simular_fila(llegadas, 180, 160)
        self.assertEqual(len(salidas), 300000)
        self.assertTrue(all(s >= l and s % 180 == 0 for s, l in zip(salidas, llegadas)))


if __name__ == "__main__":
    unittest.main()
