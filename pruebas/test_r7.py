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


if __name__ == "__main__":
    unittest.main()
