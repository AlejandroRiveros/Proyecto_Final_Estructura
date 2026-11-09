import os
import random
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from motor import simular_fila


def fila_a_lo_bruto(llegadas, frecuencia, capacidad):
    """Recorre las salidas una por una (sin saltos). Fuera de motor/ vale sorted."""
    orden = sorted(llegadas)
    esperas = []
    t = 0
    i = 0
    while i < len(orden):
        suben = 0
        while i < len(orden) and orden[i] <= t and suben < capacidad:
            esperas.append(t - orden[i])
            i += 1
            suben += 1
        t += frecuencia
    return esperas


class TestR10(unittest.TestCase):
    def test_ejemplo_fifo_y_empates(self):
        # Minuto 0 sube el primero; minuto 2 el primero de los que llegaron en 1;
        # minuto 4 el otro del minuto 1 (ya esperaba antes del que llegó en 4).
        self.assertEqual(simular_fila([0, 1, 1, 4], 2, 1), [0, 1, 3, 2])

    def test_sin_llegadas(self):
        self.assertEqual(simular_fila([], 5, 10), [])

    def test_parametros_invalidos(self):
        self.assertIsNone(simular_fila([0, 1], 0, 3))
        self.assertIsNone(simular_fila([0, 1], 5, 0))

    def test_llega_justo_cuando_sale(self):
        self.assertEqual(simular_fila([5, 5], 5, 2), [0, 0])

    def test_cupo_lleno_espera_otro_bus(self):
        self.assertEqual(simular_fila([0, 0, 0], 10, 2), [0, 0, 10])

    def test_salta_salidas_vacias(self):
        self.assertEqual(simular_fila([1000003], 10, 1), [7])

    def test_desordenadas_y_no_modifica_la_entrada(self):
        llegadas = [4, 1, 0, 1]
        self.assertEqual(simular_fila(llegadas, 2, 1), [0, 1, 3, 2])
        self.assertEqual(llegadas, [4, 1, 0, 1])

    def test_contra_calculo_bruto(self):
        azar = random.Random(10)
        for _ in range(300):
            n = azar.randrange(0, 60)
            llegadas = [azar.randrange(0, 120) for _ in range(n)]
            f = azar.randrange(1, 15)
            c = azar.randrange(1, 6)
            self.assertEqual(simular_fila(llegadas, f, c), fila_a_lo_bruto(llegadas, f, c),
                             (llegadas, f, c))

    def test_cientos_de_miles(self):
        llegadas = [i // 50 for i in range(300000)]
        esperas = simular_fila(llegadas, 3, 160)
        self.assertEqual(len(esperas), 300000)


if __name__ == "__main__":
    unittest.main()
