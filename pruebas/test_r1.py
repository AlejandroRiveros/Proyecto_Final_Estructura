import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from motor import Red
from motor.estructuras import TablaHash


class TestTablaHash(unittest.TestCase):
    def test_poner_obtener_eliminar(self):
        t = TablaHash()
        for i in range(1000):
            t.poner("CLAVE %d" % i, i)
        self.assertEqual(len(t), 1000)
        self.assertEqual(t.obtener("CLAVE 500"), 500)
        self.assertIsNone(t.obtener("NO ESTA"))
        t.poner("CLAVE 500", -1)
        self.assertEqual(t.obtener("CLAVE 500"), -1)
        self.assertEqual(len(t), 1000)
        self.assertTrue(t.eliminar("CLAVE 500"))
        self.assertFalse(t.contiene("CLAVE 500"))
        self.assertFalse(t.eliminar("CLAVE 500"))
        self.assertEqual(len(t), 999)


class TestR1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.red = Red(os.path.join(RAIZ, "datos"))

    def test_existe_y_abierta(self):
        self.assertEqual(self.red.estado("CALLE 26"), "abierta")
        self.assertEqual(self.red.estado("PORTAL NORTE"), "abierta")

    def test_no_existe(self):
        self.assertIsNone(self.red.estado("CALLE 999"))
        self.assertIsNone(self.red.estado(""))

    def test_nombre_exacto(self):
        self.assertIsNone(self.red.estado("calle 26"))
        self.assertIsNone(self.red.estado("CALLE 2"))

    def test_cerrada(self):
        self.red._estaciones.obtener("CALLE 26").abierta = False
        self.assertEqual(self.red.estado("CALLE 26"), "cerrada")
        self.red._estaciones.obtener("CALLE 26").abierta = True


if __name__ == "__main__":
    unittest.main()
