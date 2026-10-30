import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from motor import Red


class TestR9(unittest.TestCase):
    def setUp(self):
        self.red = Red(os.path.join(RAIZ, "datos"))
        self.ida = self.red.recorrido("1-1")

    def test_nada_que_deshacer(self):
        self.assertFalse(self.red.deshacer())
        self.assertFalse(self.red.rehacer())

    def test_orden_correcto(self):
        self.red.cerrar("CALLE 26")
        self.red.quitar_parada("1-1", "RECINTO FERIAL")
        self.assertTrue(self.red.deshacer())
        self.assertEqual(self.red.recorrido("1-1"), self.ida)
        self.assertEqual(self.red.estado("CALLE 26"), "cerrada")
        self.assertTrue(self.red.deshacer())
        self.assertEqual(self.red.estado("CALLE 26"), "abierta")
        self.assertEqual(self.red.autocompletar("CALLE 26", 1), ["CALLE 26"])
        self.assertTrue(self.red.rehacer())
        self.assertEqual(self.red.estado("CALLE 26"), "cerrada")
        self.assertTrue(self.red.rehacer())
        self.assertEqual(self.red.recorrido("1-1"), self.ida[:1] + self.ida[2:])
        self.assertFalse(self.red.rehacer())

    def test_cambio_nuevo_borra_rehacer(self):
        self.red.cerrar("CALLE 26")
        self.red.deshacer()
        self.red.cerrar("CALLE 100")
        self.assertFalse(self.red.rehacer())
        self.assertEqual(self.red.estado("CALLE 26"), "abierta")

    def test_quitar_primera_y_ultima(self):
        self.red.quitar_parada("1-1", self.ida[0])
        self.red.quitar_parada("1-1", self.ida[-1])
        self.red.deshacer()
        self.red.deshacer()
        self.assertEqual(self.red.recorrido("1-1"), self.ida)
        self.assertEqual(self.red.recorrido("1-1", al_reves=True), self.ida[::-1])

    def test_agregar_y_reabrir(self):
        self.red.agregar_parada("1-1", "CALLE 26", "RECINTO FERIAL")
        self.red.cerrar("CALLE 45")
        self.red.reabrir("CALLE 45")
        self.red.deshacer()
        self.assertEqual(self.red.estado("CALLE 45"), "cerrada")
        self.red.deshacer()
        self.red.deshacer()
        self.assertEqual(self.red.recorrido("1-1"), self.ida)
        self.assertEqual(self.red.estado("CALLE 45"), "abierta")

    def test_cambio_sin_efecto_no_se_registra(self):
        self.red.cerrar("NO EXISTE")
        self.red.quitar_parada("1-1", "NO ESTA")
        self.assertFalse(self.red.deshacer())


if __name__ == "__main__":
    unittest.main()
