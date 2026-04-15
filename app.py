from flask import Flask, render_template, request, redirect, session
import json

app = Flask(__name__)
app.secret_key = "clave_secreta"

# 🔐 Usuario simple
USUARIO = "admin"
PASSWORD = "1234"

# ------------------ DATOS ------------------
def cargar_datos():
    try:
        with open("data.json", "r") as archivo:
            return json.load(archivo)
    except:
        return []

def guardar_datos(equipos):
    with open("data.json", "w") as archivo:
        json.dump(equipos, archivo, indent=4)

# ------------------ LOGIN ------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        if usuario == USUARIO and password == PASSWORD:
            session["usuario"] = usuario
            return redirect("/")
        else:
            return "Credenciales incorrectas"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect("/login")

# ------------------ SISTEMA ------------------

@app.route("/")
def inicio():
    if "usuario" not in session:
        return redirect("/login")

    equipos = cargar_datos()
    return render_template("index.html", equipos=equipos)

@app.route("/agregar", methods=["POST"])
def agregar():
    if "usuario" not in session:
        return redirect("/login")

    equipos = cargar_datos()
    codigo = request.form["codigo"].strip().upper()

    for e in equipos:
        if e.get("codigo") == codigo:
            return "Ese código ya existe ⚠️"

    nuevo = {
        "codigo": codigo,
        "nombre": request.form["nombre"],
        "serial": request.form["serial"],
        "ubicacion": request.form["ubicacion"],
        "marca": request.form["marca"],
        "estado": request.form["estado"],
        "mantenimiento": request.form["mantenimiento"],
    }

    equipos.append(nuevo)
    guardar_datos(equipos)

    return redirect("/")

@app.route("/eliminar/<codigo>")
def eliminar(codigo):
    if "usuario" not in session:
        return redirect("/login")

    equipos = cargar_datos()
    equipos = [e for e in equipos if e.get("codigo") != codigo]

    guardar_datos(equipos)

    return redirect("/")

@app.route("/editar/<codigo>", methods=["GET", "POST"])
def editar(codigo):
    if "usuario" not in session:
        return redirect("/login")

    equipos = cargar_datos()

    for e in equipos:
        if e.get("codigo") == codigo:

            if request.method == "POST":
                e["nombre"] = request.form["nombre"]
                e["serial"] = request.form["serial"]
                e["ubicacion"] = request.form["ubicacion"]
                e["marca"] = request.form["marca"]
                e["estado"] = request.form["estado"]
                e["mantenimiento"] = request.form["mantenimiento"]

                guardar_datos(equipos)
                return redirect("/")

            return render_template("editar.html", equipo=e)

    return "Equipo no encontrado"

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(debug=True)