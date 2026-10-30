import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from motor import Red
from motor.estructuras import ListaDoble


class TestListaDoble(unittest.TestCase):
    def test_operaciones(self):
        l = ListaDoble()
        a = l.agregar_al_final("A")
        c = l.agregar_al_final("C")
        l.insertar_despues(a, "B")
        d = l.insertar_despues(c, "D")
        self.assertEqual(l.a_lista(), ["A", "B", "C", "D"])
        self.assertEqual(l.a_lista(al_reves=True), ["D", "C", "B", "A"])
        l.quitar(a)
        l.quitar(d)
        self.assertEqual(l.a_lista(), ["B", "C"])
        self.assertEqual(l.a_lista(al_reves=True), ["C", "B"])
        self.assertEqual(len(l), 2)


class TestCargaRutas(unittest.TestCase):
    def test_carga(self):
        red = Red(os.path.join(RAIZ, "datos"))
        ruta = red._rutas.obtener("1-1")
        self.assertEqual(ruta.paradas.a_lista()[:4],
                         ["UNIVERSIDADES", "RECINTO FERIAL", "EL TIEMPO - MALOKA", "PORTAL ELDORADO"])
        self.assertEqual(len(red._rutas), 181)


class TestR7Publico(unittest.TestCase):
    def setUp(self):
        self.red = Red(os.path.join(RAIZ, "datos"))
        self.ida = self.red.recorrido("1-1")

    def test_recorrido(self):
        self.assertEqual(self.ida[:2], ["UNIVERSIDADES", "RECINTO FERIAL"])
        vuelta = self.red.recorrido("1-1", al_reves=True)
        self.assertEqual(vuelta, self.ida[::-1])
        self.assertEqual(self.red.recorrido("NO EXISTE"), [])

    def test_agregar(self):
        self.assertTrue(self.red.agregar_parada("1-1", "CALLE 26", "RECINTO FERIAL"))
        self.assertEqual(self.red.recorrido("1-1")[:3], ["UNIVERSIDADES", "RECINTO FERIAL", "CALLE 26"])
        ultima = self.ida[-1]
        self.assertTrue(self.red.agregar_parada("1-1", "CALLE 100", ultima))
        self.assertEqual(self.red.recorrido("1-1")[-1], "CALLE 100")
        self.assertEqual(self.red.recorrido("1-1", al_reves=True)[0], "CALLE 100")

    def test_agregar_casos_sin_cambio(self):
        self.assertFalse(self.red.agregar_parada("NO EXISTE", "CALLE 26", "RECINTO FERIAL"))
        self.assertFalse(self.red.agregar_parada("1-1", "CALLE 26", "CALLE 100"))
        self.assertFalse(self.red.agregar_parada("1-1", "RECINTO FERIAL", "UNIVERSIDADES"))
        self.assertFalse(self.red.agregar_parada("1-1", "ESTACION INVENTADA", "UNIVERSIDADES"))
        self.assertEqual(self.red.recorrido("1-1"), self.ida)

    def test_quitar(self):
        primera = self.ida[0]
        ultima = self.ida[-1]
        self.assertTrue(self.red.quitar_parada("1-1", primera))
        self.assertTrue(self.red.quitar_parada("1-1", ultima))
        self.assertEqual(self.red.recorrido("1-1"), self.ida[1:-1])
        self.assertEqual(self.red.recorrido("1-1", al_reves=True), self.ida[1:-1][::-1])
        self.assertFalse(self.red.quitar_parada("1-1", primera))
        self.assertFalse(self.red.quitar_parada("NO EXISTE", "CALLE 26"))

    def test_quitar_y_volver_a_agregar(self):
        self.assertTrue(self.red.quitar_parada("1-1", "RECINTO FERIAL"))
        self.assertTrue(self.red.agregar_parada("1-1", "RECINTO FERIAL", "UNIVERSIDADES"))
        self.assertEqual(self.red.recorrido("1-1"), self.ida)


if __name__ == "__main__":
    unittest.main()
