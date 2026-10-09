import math

def calculadora():
    while True:
        print("\n========== CALCULADORA ==========")
        print("1. Sumar")
        print("2. Restar")
        print("3. Multiplicar")
        print("4. Dividir")
        print("5. Potencia")
        print("6. Raíz cuadrada")
        print("7. Salir")
        print("=================================")

        opcion = input("Selecciona una opción: ")

        if opcion == "7":
            print("¡Gracias por usar la calculadora!")
            break

        if opcion not in ["1", "2", "3", "4", "5", "6"]:
            print("Opción no válida. Intenta nuevamente.")
            continue

        try:
            num1 = float(input("Ingresa el primer número: "))

            if opcion != "6":
                num2 = float(input("Ingresa el segundo número: "))

            if opcion == "1":
                resultado = num1 + num2

            elif opcion == "2":
                resultado = num1 - num2

            elif opcion == "3":
                resultado = num1 * num2

            elif opcion == "4":
                if num2 == 0:
                    print("Error: No se puede dividir entre cero.")
                    continue
                resultado = num1 / num2

            elif opcion == "5":
                resultado = num1 ** num2

            elif opcion == "6":
                if num1 < 0:
                    print("Error: No se puede calcular la raíz de un número negativo.")
                    continue
                resultado = math.sqrt(num1)

            print(f"\nResultado: {resultado}")

        except ValueError:
            print("Error: Ingresa solamente números válidos.")
        except OverflowError:
            print("Error: El resultado es demasiado grande.")


if __name__ == "__main__":
    calculadora()