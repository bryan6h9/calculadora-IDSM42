def sumar(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Los argumentos deben ser números")
    return a + b


def restar(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Los argumentos deben ser números")
    return a - b


def multiplicar(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Los argumentos deben ser números")
    return a * b


def dividir(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Los argumentos deben ser números")
    if b == 0:
        raise ValueError("No se puede dividir entre cero")
    return a / b
