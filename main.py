import json

# ------------------ GUARDAR DATOS ------------------
def guardar_datos():
    with open("data.json", "w") as archivo:
        json.dump(equipos, archivo, indent=4)

# ------------------ CARGAR DATOS ------------------
try:
    with open("data.json", "r") as archivo:
        equipos = json.load(archivo)
except (FileNotFoundError, json.JSONDecodeError):
    equipos = []

# ------------------ VALIDACIONES ------------------
def codigo_existe(codigo):
    for e in equipos:
        if e["codigo"] == codigo:
            return True
    return False

def buscar_equipo_por_codigo(codigo):
    codigo = codigo.strip().upper()
    for i, e in enumerate(equipos):
        if e["codigo"] == codigo:
            return i
    return -1

# ------------------ REGISTRAR ------------------
def registrar_equipo():
    codigo = input("Código de inventario: ").strip().upper()

    if codigo == "":
        print("El código no puede estar vacío")
        return

    if codigo_existe(codigo):
        print("Ese código ya existe")
        return

    equipo = input("Nombre del equipo: ")
    serial = input("Serial: ")
    ubicacion = input("Ubicación: ")
    marca = input("Marca: ")
    estado = input("Estado: ")
    mantenimiento = input("Mantenimiento: ")

    datos = {
        "codigo": codigo,
        "nombre": equipo,
        "serial": serial,
        "ubicacion": ubicacion,
        "marca": marca,
        "estado": estado,
        "mantenimiento": mantenimiento,
    }

    equipos.append(datos)
    guardar_datos()

    print("Equipo guardado correctamente\n")

# ------------------ MOSTRAR ------------------
def mostrar_equipos():
    if len(equipos) == 0:
        print("No hay equipos registrados")
    else:
        for e in equipos:
            print("\n========================")
            print(f"Código: {e['codigo']}")
            print(f"Nombre: {e['nombre']}")
            print(f"Serial: {e['serial']}")
            print(f"Ubicación: {e['ubicacion']}")
            print(f"Marca: {e['marca']}")
            print(f"Estado: {e['estado']}")
            print(f"Mantenimiento: {e['mantenimiento']}")

# ------------------ ELIMINAR ------------------
def eliminar_equipo():
    codigo = input("Ingrese el código del equipo a eliminar: ")

    indice = buscar_equipo_por_codigo(codigo)

    if indice == -1:
        print("Equipo no encontrado")
        return

    confirmacion = input("¿Seguro que desea eliminar? (s/n): ").lower()

    if confirmacion == "s":
        equipos.pop(indice)
        guardar_datos()
        print("Equipo eliminado correctamente")
    else:
        print("Operación cancelada")

# ------------------ EDITAR ------------------
def editar_equipo():
    codigo = input("Ingrese el código del equipo a editar: ")

    indice = buscar_equipo_por_codigo(codigo)

    if indice == -1:
        print("Equipo no encontrado")
        return

    equipo = equipos[indice]

    print("Deje vacío si no desea cambiar el valor")

    nuevo_nombre = input(f"Nombre ({equipo['nombre']}): ") or equipo["nombre"]
    nuevo_serial = input(f"Serial ({equipo['serial']}): ") or equipo["serial"]
    nueva_ubicacion = input(f"Ubicación ({equipo['ubicacion']}): ") or equipo["ubicacion"]
    nueva_marca = input(f"Marca ({equipo['marca']}): ") or equipo["marca"]
    nuevo_estado = input(f"Estado ({equipo['estado']}): ") or equipo["estado"]
    nuevo_mantenimiento = input(f"Mantenimiento ({equipo['mantenimiento']}): ") or equipo["mantenimiento"]

    equipos[indice] = {
        "codigo": equipo["codigo"],
        "nombre": nuevo_nombre,
        "serial": nuevo_serial,
        "ubicacion": nueva_ubicacion,
        "marca": nueva_marca,
        "estado": nuevo_estado,
        "mantenimiento": nuevo_mantenimiento,
    }

    guardar_datos()
    print("Equipo actualizado correctamente")

# ------------------ MENÚ ------------------
while True:
    print("\n--- MENÚ ---")
    print("1. Registrar equipo")
    print("2. Ver equipos")
    print("3. Eliminar equipo")
    print("4. Editar equipo")
    print("5. Salir")

    opcion = input("Seleccione: ").strip()

    if opcion == "1":
        registrar_equipo()
    elif opcion == "2":
        mostrar_equipos()
    elif opcion == "3":
        eliminar_equipo()
    elif opcion == "4":
        editar_equipo()
    elif opcion == "5":
        break
    else:
        print("Opción inválida")