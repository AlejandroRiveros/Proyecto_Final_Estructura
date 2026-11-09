from motor.fila import simular_fila 

def test_simular_fila_tupla():

    resultado = simular_fila(frecuencia=10, llegadas=5)
    assert isinstance(resultado, tuple), "El resultado de la fila debe ser una tupla."
    assert len(resultado) == 2, "La tupla debe contener exactamente dos elementos."
