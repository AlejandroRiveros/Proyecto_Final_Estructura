"""Revisa con el AST que motor/ no use nada prohibido (diapositiva 9).

Buscar texto como "dict" o "{" en el código no basta: no ve dict() ni set(),
y confunde llaves dentro de comentarios o cadenas. El AST mira la estructura
real del programa, así que solo marca lo que de verdad se ejecuta.
"""
import ast
import os
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOTOR = os.path.join(RAIZ, "motor")

FUNCIONES_PROHIBIDAS = ("dict", "set", "frozenset", "sorted", "min", "max")
METODOS_PROHIBIDOS = ("sort", "index", "count", "insert")
MODULOS_PERMITIDOS = ("csv", "time", "random")
ATRIBUTOS_PROHIBIDOS = ("DictReader", "DictWriter")


def archivos_motor():
    for carpeta, _, archivos in os.walk(MOTOR):
        for nombre in archivos:
            if nombre.endswith(".py"):
                yield os.path.join(carpeta, nombre)


def problemas_en(ruta):
    with open(ruta, encoding="utf-8") as f:
        arbol = ast.parse(f.read(), ruta)
    salida = []

    def marcar(nodo, que):
        salida.append("%s:%d %s" % (os.path.relpath(ruta, RAIZ), nodo.lineno, que))

    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.Dict, ast.DictComp)):
            marcar(nodo, "diccionario literal o por comprensión")
        elif isinstance(nodo, (ast.Set, ast.SetComp)):
            marcar(nodo, "conjunto literal o por comprensión")
        elif isinstance(nodo, ast.Call):
            f = nodo.func
            if isinstance(f, ast.Name) and f.id in FUNCIONES_PROHIBIDAS:
                marcar(nodo, f.id + "()")
            elif isinstance(f, ast.Attribute) and f.attr in METODOS_PROHIBIDOS:
                marcar(nodo, "." + f.attr + "()")
            elif isinstance(f, ast.Attribute) and f.attr == "pop" and len(nodo.args) > 0:
                marcar(nodo, ".pop(i) con posición")
        elif isinstance(nodo, ast.Attribute) and nodo.attr in ATRIBUTOS_PROHIBIDOS:
            marcar(nodo, nodo.attr + " (sus filas son dict)")
        elif isinstance(nodo, ast.Compare):
            for op in nodo.ops:
                if isinstance(op, (ast.In, ast.NotIn)):
                    marcar(nodo, "operador in / not in")
        elif isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if alias.name.split(".")[0] not in MODULOS_PERMITIDOS:
                    marcar(nodo, "import " + alias.name)
        elif isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ""
            if modulo.split(".")[0] not in MODULOS_PERMITIDOS + ("motor",):
                marcar(nodo, "from " + modulo + " import ...")
    return salida


class TestProhibidos(unittest.TestCase):
    def test_motor_sin_prohibidos(self):
        problemas = []
        for ruta in archivos_motor():
            problemas.extend(problemas_en(ruta))
        self.assertEqual(problemas, [], "\n" + "\n".join(problemas))


if __name__ == "__main__":
    unittest.main()
