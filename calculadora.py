def sumar(a, b):
    a, b = float(a), float(b)
    return a + b


def restar(a, b):
    a, b = float(a), float(b)
    return a - b


def multiplicar(a, b):
    a, b = float(a), float(b)
    return a * b


def dividir(a, b):
    a, b = float(a), float(b)
    if b == 0:
        raise ValueError("No se puede dividir entre cero")
    return a / b
