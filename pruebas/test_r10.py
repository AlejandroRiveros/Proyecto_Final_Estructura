import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from motor import simular_fila


class TestR10(unittest.TestCase):
    def test_devuelve_tupla_de_dos(self):
        resultado = simular_fila(llegadas=5, frecuencia=10, capacidad=3)
        self.assertIsInstance(resultado, tuple)
        self.assertEqual(len(resultado), 2)

    def test_buses_y_pasajeros(self):
        # 5 pasajeros con cupo 3: sale un bus lleno y otro con 2.
        self.assertEqual(simular_fila(5, 10, 3), (2, 5))
        self.assertEqual(simular_fila(6, 10, 3), (2, 6))
        self.assertEqual(simular_fila(0, 10, 3), (0, 0))


if __name__ == "__main__":
    unittest.main()
