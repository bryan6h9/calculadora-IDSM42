from calculator import sumar, restar, multiplicar, dividir


def main():
    while True:
        print("\n===== CALCULADORA =====")
        print("1. Sumar")
        print("2. Restar")
        print("3. Multiplicar")
        print("4. Dividir")
        print("5. Salir")

        opcion = input("Selecciona una opción: ")

        if opcion == "5":
            print("Saliendo...")
            break

        if opcion not in ("1", "2", "3", "4"):
            print("Opción inválida")
            continue

        try:
            a = float(input("Primer número: "))
            b = float(input("Segundo número: "))

            if opcion == "1":
                resultado = sumar(a, b)
            elif opcion == "2":
                resultado = restar(a, b)
            elif opcion == "3":
                resultado = multiplicar(a, b)
            else:
                resultado = dividir(a, b)

            print("Resultado:", resultado)

        except ValueError as error:
            print("Error:", error)


if __name__ == "__main__":
    main()
