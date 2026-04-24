from flask import Flask, render_template, request, redirect, session, send_from_directory
import json
import os
import shutil
from datetime import datetime
from dateutil.relativedelta import relativedelta
from werkzeug.utils import secure_filename
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")
BACKUP_FOLDER = os.path.join(BASE_DIR, "backups")

os.makedirs(BACKUP_FOLDER, exist_ok=True)

# ------------------ CONFIGURACIÓN ------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super_clave_local")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

USUARIO = "admin"
PASSWORD = "1234"

# ------------------ DATOS ------------------

def cargar_datos():
    
    try:
        with open(DATA_FILE, "r") as archivo:
            return json.load(archivo)
    except:
        return []

    hoy = datetime.today().date()

    for e in equipos:

        # 🔧 MANTENIMIENTO
        try:
            ultimo = datetime.strptime(e.get("ultimo_mantenimiento", ""), "%Y-%m-%d").date()
            frecuencia = int(e.get("frecuencia_mantenimiento", "0"))

            if frecuencia > 0:
                proximo = ultimo + relativedelta(months=frecuencia)
                e["proximo_mantenimiento"] = str(proximo)

                dias = (proximo - hoy).days

                if dias < 0:
                    e["alerta"] = "rojo"
                elif dias <= 30:
                    e["alerta"] = "amarillo"
                else:
                    e["alerta"] = "verde"
            else:
                e["alerta"] = "gris"

        except:
            e["alerta"] = "gris"

        # 📏 METROLOGÍA
        try:
            if e.get("metrologia", "").strip().lower() == "si":

                ultima_cal = datetime.strptime(
                    e.get("ultima_calibracion", ""), "%Y-%m-%d"
                ).date()

                freq_m = int(e.get("frecuencia_metrologia", "0"))

                if freq_m > 0:
                    proximo_m = ultima_cal + relativedelta(months=freq_m)
                    e["proximo_metrologia"] = str(proximo_m)

                    dias_m = (proximo_m - hoy).days

                    if dias_m < 0:
                        e["alerta_metro"] = "rojo"
                    elif dias_m <= 30:
                        e["alerta_metro"] = "amarillo"
                    else:
                        e["alerta_metro"] = "verde"
                else:
                    e["alerta_metro"] = "gris"
            else:
                e["alerta_metro"] = "no_aplica"

        except:
            e["alerta_metro"] = "gris"

    return equipos


def guardar_datos(equipos):

    # 💾 Guardar principal
    with open(DATA_FILE, "w") as archivo:
        json.dump(equipos, archivo, indent=4)

    # 🧠 Backup
    from datetime import datetime
    import shutil

    fecha = datetime.now().strftime("%Y-%m-%d")
    backup_nombre = os.path.join(BACKUP_FOLDER, f"backup_{fecha}.json")

    if not os.path.exists(backup_nombre):
        shutil.copy(DATA_FILE, backup_nombre)


# ------------------ LOGIN ------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["usuario"] == USUARIO and request.form["password"] == PASSWORD:
            session["usuario"] = USUARIO
            return redirect("/")
        return "Credenciales incorrectas"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect("/login")


# ------------------ INICIO ------------------

@app.route("/")
def inicio():
    if "usuario" not in session:
        return redirect("/login")

    equipos = cargar_datos()

    # 🔧 CONTADORES
    rojos = sum(1 for e in equipos if e.get("alerta") == "rojo")
    amarillos = sum(1 for e in equipos if e.get("alerta") == "amarillo")
    verdes = sum(1 for e in equipos if e.get("alerta") == "verde")
    grises = sum(1 for e in equipos if e.get("alerta") == "gris")

    # 📏 METROLOGÍA
    rojos_m = sum(1 for e in equipos if e.get("alerta_metro") == "rojo")
    amarillos_m = sum(1 for e in equipos if e.get("alerta_metro") == "amarillo")
    verdes_m = sum(1 for e in equipos if e.get("alerta_metro") == "verde")

    return render_template("index.html",
        equipos=equipos,
        rojos=rojos,
        amarillos=amarillos,
        verdes=verdes,
        grises=grises,
        rojos_m=rojos_m,
        amarillos_m=amarillos_m,
        verdes_m=verdes_m
    )


# ------------------ CRUD ------------------

@app.route("/agregar", methods=["POST"])
def agregar():
    if "usuario" not in session:
        return redirect("/login")

    equipos = cargar_datos()

    codigo = request.form.get("codigo", "").strip().upper()

    # 🚨 VALIDACIÓN
    if not codigo:
        return "El código es obligatorio"

    for e in equipos:
        if e.get("codigo") == codigo:
            return "Ese código ya existe ⚠️"

    nuevo = {
        "codigo": codigo,
        "nombre": request.form.get("nombre", ""),
        "marca": request.form.get("marca", ""),
        "modelo": request.form.get("modelo", ""),
        "serie": request.form.get("serie", ""),
        "ubicacion": request.form.get("ubicacion", ""),
        "clase": request.form.get("clase", ""),
        "invima": request.form.get("invima", ""),
        "fecha_compra": request.form.get("fecha_compra", ""),
        "proveedor": request.form.get("proveedor", ""),
        "fecha_instalacion": request.form.get("fecha_instalacion", ""),
        "frecuencia_mantenimiento": int(request.form.get("frecuencia_mantenimiento") or 0),
        "ultimo_mantenimiento": request.form.get("ultimo_mantenimiento", ""),
        "metrologia": request.form.get("metrologia", "No"),
        "frecuencia_metrologia": int(request.form.get("frecuencia_metrologia") or 0),
        "ultima_calibracion": request.form.get("ultima_calibracion", ""),
        "observaciones": request.form.get("observaciones", "")
    }

    equipos.append(nuevo)
    guardar_datos(equipos)

    return redirect("/")


@app.route("/eliminar/<codigo>")
def eliminar(codigo):
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

                if "historial" not in e:
                    e["historial"] = []

                # 🔧 mantenimiento
                if request.form.get("ultimo_mantenimiento") != e.get("ultimo_mantenimiento"):
                    e["historial"].append({
                        "tipo": "mantenimiento",
                        "fecha": request.form.get("ultimo_mantenimiento")
                    })

                # 📏 calibración
                if request.form.get("ultima_calibracion") != e.get("ultima_calibracion"):
                    e["historial"].append({
                        "tipo": "calibracion",
                        "fecha": request.form.get("ultima_calibracion")
                    })

                for key in request.form:
                    e[key] = request.form[key]

                guardar_datos(equipos)
                return redirect("/")

            return render_template("editar.html", equipo=e)

    return "Equipo no encontrado"


# ------------------ HISTORIAL ------------------

@app.route("/historial/<codigo>")
def historial(codigo):
    if "usuario" not in session:
        return redirect("/login")

    equipos = cargar_datos()

    for e in equipos:
        if e.get("codigo") == codigo:
            return render_template("historial.html", equipo=e)

    return "Equipo no encontrado"


# ------------------ SUBIR ARCHIVOS ------------------

@app.route("/subir_certificado/<codigo>/<int:index>", methods=["POST"])
def subir_certificado(codigo, index):

    if "usuario" not in session:
        return redirect("/login")

    equipos = cargar_datos()
    archivo = request.files.get("archivo")

    if not archivo or archivo.filename == "":
        return "No se seleccionó archivo"

    # 🔐 Validar tipo de archivo
    if not archivo.filename.lower().endswith((".pdf", ".jpg", ".png")):
        return "Formato no permitido (solo PDF, JPG, PNG)"

    # 🕒 Nombre único
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    nombre_archivo = f"{codigo}_{timestamp}_{secure_filename(archivo.filename)}"
    ruta = os.path.join(app.config["UPLOAD_FOLDER"], nombre_archivo)

    archivo.save(ruta)

    # 🔄 Guardar en historial
    for e in equipos:
        if e.get("codigo") == codigo:

            if "historial" in e and len(e["historial"]) > index:
                e["historial"][index]["archivo"] = nombre_archivo

    guardar_datos(equipos)

    return redirect(f"/historial/{codigo}")

@app.route("/uploads/<filename>")
def descargar_archivo(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ------------------ PDF ------------------

@app.route("/reporte/<codigo>")
def reporte(codigo):

    equipos = cargar_datos()

    for e in equipos:
        if e.get("codigo") == codigo:

            archivo = f"reporte_{codigo}.pdf"
            doc = SimpleDocTemplate(archivo)
            styles = getSampleStyleSheet()

            contenido = []

            contenido.append(Paragraph("<b>REPORTE BIOMÉDICO</b>", styles["Title"]))
            contenido.append(Spacer(1, 10))

            for k, v in e.items():
                if k != "historial":
                    contenido.append(Paragraph(f"{k}: {v}", styles["Normal"]))

            contenido.append(Spacer(1, 10))
            contenido.append(Paragraph("<b>Historial</b>", styles["Heading2"]))

            for h in e.get("historial", []):
                contenido.append(Paragraph(f"{h['tipo']} - {h['fecha']}", styles["Normal"]))

            doc.build(contenido)

            return send_from_directory(".", archivo, as_attachment=True)

    return "No encontrado"


# ------------------ CRONOGRAMA ------------------

@app.route("/cronograma")
def cronograma():
    if "usuario" not in session:
        return redirect("/login")

    equipos = cargar_datos()

    # 🔎 FILTROS
    filtro_mes = request.args.get("mes")
    filtro_ubicacion = request.args.get("ubicacion")

    eventos = []

    for e in equipos:

        # 🔧 MANTENIMIENTO
        if e.get("proximo_mantenimiento"):
            eventos.append({
                "codigo": e.get("codigo"),
                "nombre": e.get("nombre"),
                "tipo": "Mantenimiento",
                "fecha": e.get("proximo_mantenimiento"),
                "ubicacion": e.get("ubicacion")
            })

        # 📏 CALIBRACIÓN
        if e.get("metrologia", "").lower() == "si":
            if e.get("proximo_metrologia"):
                eventos.append({
                    "codigo": e.get("codigo"),
                    "nombre": e.get("nombre"),
                    "tipo": "Calibración",
                    "fecha": e.get("proximo_metrologia"),
                    "ubicacion": e.get("ubicacion")
                })

    # 🔥 FILTRAR
    if filtro_mes:
        eventos = [e for e in eventos if e["fecha"].startswith(filtro_mes)]

    if filtro_ubicacion:
        eventos = [e for e in eventos if filtro_ubicacion.lower() in (e["ubicacion"] or "").lower()]

    # ORDENAR
    eventos.sort(key=lambda x: x["fecha"])

    return render_template("cronograma.html", eventos=eventos)


# ------------------ RUN ------------------

if __name__ == "__main__":
    app.run(debug=True)