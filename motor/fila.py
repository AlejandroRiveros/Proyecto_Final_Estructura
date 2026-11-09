# R10
from motor.estructuras.cola import Cola


def simular_fila(llegadas, frecuencia, capacidad):
    cola_pasajeros = Cola()
    buses_salidos = 0
    pasajeros_transportados = 0
    tiempo_actual = 0
    
    # Simulamos la llegada de pasajeros
    # (dependiendo de cómo te lo pida el profesor, puedes ajustar la lógica de tiempo)
    for i in range(llegadas):
        cola_pasajeros.encolar(f"Pasajero_{i+1}")
        
    # Simulación de salida de buses
    while not cola_pasajeros.esta_vacia():
        cupos_disponibles = capacidad
        while cupos_disponibles > 0 and not cola_pasajeros.esta_vacia():
            cola_pasajeros.desencolar()
            pasajeros_transportados += 1
            cupos_disponibles -= 1
        buses_salidos += 1
        tiempo_actual += frecuencia

    return {
        (buses_salidos, pasajeros_transportados)
    }
