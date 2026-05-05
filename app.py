# ------------------ IMPORTS ------------------
from flask import Flask, render_template, request, redirect, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from dateutil.relativedelta import relativedelta
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os
import json
import shutil

# ------------------ CONFIG ------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")
BACKUP_FOLDER = os.path.join(BASE_DIR, "backups")

os.makedirs(BACKUP_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave_local")

# DB
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "database.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# uploads
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ------------------ MODELOS ------------------

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))

class Equipo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True)
    nombre = db.Column(db.String(100))
    marca = db.Column(db.String(100))
    modelo = db.Column(db.String(100))
    serie = db.Column(db.String(100))
    ubicacion = db.Column(db.String(100))
    clase = db.Column(db.String(50))
    invima = db.Column(db.String(100))
    fecha_compra = db.Column(db.String(20))
    proveedor = db.Column(db.String(100))
    fecha_instalacion = db.Column(db.String(20))
    frecuencia_mantenimiento = db.Column(db.Integer)
    ultimo_mantenimiento = db.Column(db.String(20))
    metrologia = db.Column(db.String(10))
    frecuencia_metrologia = db.Column(db.Integer)
    ultima_calibracion = db.Column(db.String(20))
    observaciones = db.Column(db.Text)

class Historial(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    equipo_id = db.Column(
        db.Integer,
        db.ForeignKey("equipo.id")
    )

    tipo = db.Column(db.String(50))
    fecha = db.Column(db.String(20))
    archivo = db.Column(db.String(200))

    equipo = db.relationship(
        "Equipo",
        backref="historiales"
    )    

# ------------------ UTILIDADES ------------------

def calcular_alertas(equipos):

    hoy = datetime.today().date()

    for e in equipos:

        # 🔧 MANTENIMIENTO
        try:
            if e.frecuencia_mantenimiento and e.ultimo_mantenimiento:

                ultimo = datetime.strptime(e.ultimo_mantenimiento, "%Y-%m-%d").date()
                proximo = ultimo + relativedelta(months=e.frecuencia_mantenimiento)

                e.proximo_mantenimiento = str(proximo)

                dias = (proximo - hoy).days

                if dias < 0:
                    e.alerta = "rojo"
                elif dias <= 30:
                    e.alerta = "amarillo"
                else:
                    e.alerta = "verde"
            else:
                e.alerta = "gris"

        except:
            e.alerta = "gris"

        # 📏 METROLOGÍA
        try:
            if (e.metrologia or "").lower() == "si":

                if e.frecuencia_metrologia and e.ultima_calibracion:

                    ultima = datetime.strptime(e.ultima_calibracion, "%Y-%m-%d").date()
                    proximo = ultima + relativedelta(months=e.frecuencia_metrologia)

                    e.proximo_metrologia = str(proximo)

                    dias = (proximo - hoy).days

                    if dias < 0:
                        e.alerta_metro = "rojo"
                    elif dias <= 30:
                        e.alerta_metro = "amarillo"
                    else:
                        e.alerta_metro = "verde"
                else:
                    e.alerta_metro = "gris"
            else:
                e.alerta_metro = "no_aplica"

        except:
            e.alerta_metro = "gris"

    return equipos

# ------------------ CARGAR DATOS (HIBRIDO) ------------------

def cargar_datos():
    try:
        equipos_db = Equipo.query.all()

        if equipos_db:
            equipos = []
            for e in equipos_db:
                equipos.append({
                    "codigo": e.codigo,
                    "nombre": e.nombre,
                    "marca": e.marca,
                    "modelo": e.modelo,
                    "serie": e.serie,
                    "ubicacion": e.ubicacion,
                    "clase": e.clase,
                    "invima": e.invima,
                    "fecha_compra": e.fecha_compra,
                    "proveedor": e.proveedor,
                    "fecha_instalacion": e.fecha_instalacion,
                    "frecuencia_mantenimiento": e.frecuencia_mantenimiento,
                    "ultimo_mantenimiento": e.ultimo_mantenimiento,
                    "metrologia": e.metrologia,
                    "frecuencia_metrologia": e.frecuencia_metrologia,
                    "ultima_calibracion": e.ultima_calibracion,
                    "observaciones": e.observaciones
                })
            return equipos
    except:
        pass

    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def guardar_datos(equipos):
    with open(DATA_FILE, "w") as f:
        json.dump(equipos, f, indent=4)

# ------------------ MIGRACIÓN ------------------

def convertir_frecuencia(valor):
    if not valor:
        return 0

    valor = str(valor).lower().strip()

    mapa = {
        "mensual": 1,
        "bimensual": 2,
        "trimestral": 3,
        "semestral": 6,
        "anual": 12
    }

    # si ya es número
    if valor.isdigit():
        return int(valor)

    return mapa.get(valor, 0)

def migrar_json_a_db():
    try:
        with open(DATA_FILE, "r") as f:
            equipos_json = json.load(f)
    except:
        return "No hay JSON"

    contador = 0

    for e in equipos_json:

        codigo = e.get("codigo", "").strip().upper()

        if not codigo:
            continue

        existe = Equipo.query.filter_by(codigo=codigo).first()

        if not existe:
            nuevo = Equipo(
                codigo=codigo,
                nombre=e.get("nombre"),
                marca=e.get("marca"),
                modelo=e.get("modelo"),
                serie=e.get("serie"),
                ubicacion=e.get("ubicacion"),
                clase=e.get("clase"),
                invima=e.get("invima"),
                fecha_compra=e.get("fecha_compra"),
                proveedor=e.get("proveedor"),
                fecha_instalacion=e.get("fecha_instalacion"),
                frecuencia_mantenimiento=convertir_frecuencia(e.get("frecuencia_mantenimiento")),
                ultimo_mantenimiento=e.get("ultimo_mantenimiento"),
                metrologia=e.get("metrologia"),
                frecuencia_metrologia=convertir_frecuencia(e.get("frecuencia_metrologia")),
                ultima_calibracion=e.get("ultima_calibracion"),
                observaciones=e.get("observaciones")
            )

            db.session.add(nuevo)
            contador += 1

    db.session.commit()

    return f"Migración completada: {contador} equipos insertados"

# ------------------ LOGIN ------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = Usuario.query.filter_by(usuario=request.form["usuario"]).first()

        if user and check_password_hash(user.password, request.form["password"]):
            session["usuario"] = user.usuario
            return redirect("/")

        return "Credenciales incorrectas"

    return render_template("login.html")

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        usuario = request.form["usuario"]

        if Usuario.query.filter_by(usuario=usuario).first():
            return "Usuario ya existe"

        nuevo = Usuario(
            usuario=usuario,
            password=generate_password_hash(request.form["password"])
        )

        db.session.add(nuevo)
        db.session.commit()

        return redirect("/login")

    return render_template("registro.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ------------------ INICIO ------------------

@app.route("/")
def inicio():
    if "usuario" not in session:
        return redirect("/login")

    equipos = Equipo.query.all()

    equipos = calcular_alertas(equipos)

    # 🔧 CONTADORES
    rojos = sum(1 for e in equipos if e.alerta == "rojo")
    amarillos = sum(1 for e in equipos if e.alerta == "amarillo")
    verdes = sum(1 for e in equipos if e.alerta == "verde")
    grises = sum(1 for e in equipos if e.alerta == "gris")

    # 📏 METROLOGÍA
    rojos_m = sum(1 for e in equipos if e.alerta_metro == "rojo")
    amarillos_m = sum(1 for e in equipos if e.alerta_metro == "amarillo")
    verdes_m = sum(1 for e in equipos if e.alerta_metro == "verde")

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

    codigo = request.form.get("codigo", "").strip().upper()

    # 🚨 Validación
    if not codigo:
        return "El código es obligatorio"

    # 🚨 Validar duplicado en DB
    existe = Equipo.query.filter_by(codigo=codigo).first()
    if existe:
        return "Ese código ya existe ⚠️"

    # ✅ Crear nuevo equipo SOLO en DB
    nuevo = Equipo(
        codigo=codigo,
        nombre=request.form.get("nombre"),
        marca=request.form.get("marca"),
        modelo=request.form.get("modelo"),
        serie=request.form.get("serie"),
        ubicacion=request.form.get("ubicacion"),
        clase=request.form.get("clase"),
        invima=request.form.get("invima"),
        fecha_compra=request.form.get("fecha_compra"),
        proveedor=request.form.get("proveedor"),
        fecha_instalacion=request.form.get("fecha_instalacion"),
        frecuencia_mantenimiento=int(request.form.get("frecuencia_mantenimiento") or 0),
        ultimo_mantenimiento=request.form.get("ultimo_mantenimiento"),
        metrologia=request.form.get("metrologia"),
        frecuencia_metrologia=int(request.form.get("frecuencia_metrologia") or 0),
        ultima_calibracion=request.form.get("ultima_calibracion"),
        observaciones=request.form.get("observaciones")
    )

    db.session.add(nuevo)
    db.session.commit()

    return redirect("/")

@app.route("/eliminar/<codigo>")
def eliminar(codigo):
    if "usuario" not in session:
        return redirect("/login")

    equipo = Equipo.query.filter_by(codigo=codigo).first()

    if equipo:
        db.session.delete(equipo)
        db.session.commit()

    return redirect("/")

@app.route("/editar/<codigo>", methods=["GET", "POST"])
def editar(codigo):
    if "usuario" not in session:
        return redirect("/login")

    equipo = Equipo.query.filter_by(codigo=codigo).first()

    if not equipo:
        return "Equipo no encontrado"

    if request.method == "POST":

        # 🔧 historial mantenimiento
        nuevo_mantenimiento = request.form.get("ultimo_mantenimiento")

        if (
            nuevo_mantenimiento
            and nuevo_mantenimiento != equipo.ultimo_mantenimiento
        ):

            historial = Historial(
                equipo_id=equipo.id,
                tipo="mantenimiento",
                fecha=nuevo_mantenimiento
            )

            db.session.add(historial)

        # 📏 historial calibración
        nueva_calibracion = request.form.get("ultima_calibracion")

        if (
            nueva_calibracion
            and nueva_calibracion != equipo.ultima_calibracion
        ):

            historial = Historial(
                equipo_id=equipo.id,
                tipo="calibracion",
                fecha=nueva_calibracion
            )

            db.session.add(historial)

        # actualizar campos
        equipo.nombre = request.form.get("nombre")
        equipo.marca = request.form.get("marca")
        equipo.modelo = request.form.get("modelo")
        equipo.serie = request.form.get("serie")
        equipo.ubicacion = request.form.get("ubicacion")
        equipo.clase = request.form.get("clase")
        equipo.invima = request.form.get("invima")
        equipo.fecha_compra = request.form.get("fecha_compra")
        equipo.proveedor = request.form.get("proveedor")
        equipo.fecha_instalacion = request.form.get("fecha_instalacion")
        equipo.frecuencia_mantenimiento = int(request.form.get("frecuencia_mantenimiento") or 0)
        equipo.ultimo_mantenimiento = request.form.get("ultimo_mantenimiento")
        equipo.metrologia = request.form.get("metrologia")
        equipo.frecuencia_metrologia = int(request.form.get("frecuencia_metrologia") or 0)
        equipo.ultima_calibracion = request.form.get("ultima_calibracion")
        equipo.observaciones = request.form.get("observaciones")

        db.session.commit()

        return redirect("/")

    return render_template("editar.html", equipo=equipo)

@app.route("/cronograma")
def cronograma():

    if "usuario" not in session:
        return redirect("/login")

    equipos = Equipo.query.all()
    eventos = []

    for e in equipos:

        # 🔧 MANTENIMIENTO
        try:
            if (
                e.frecuencia_mantenimiento
                and e.ultimo_mantenimiento
                and str(e.ultimo_mantenimiento).strip() != ""
            ):

                ultimo = datetime.strptime(
                    e.ultimo_mantenimiento,
                    "%Y-%m-%d"
                ).date()

                proximo = ultimo + relativedelta(
                    months=e.frecuencia_mantenimiento
                )

                eventos.append({
                    "codigo": e.codigo,
                    "nombre": e.nombre,
                    "tipo": "Mantenimiento",
                    "fecha": proximo.strftime("%Y-%m-%d"),
                    "ubicacion": e.ubicacion
                })

        except Exception as error:
            print("Error mantenimiento:", error)

        # 📏 CALIBRACIÓN
        try:
            if (
                (e.metrologia or "").lower() == "si"
                and e.frecuencia_metrologia
                and e.ultima_calibracion
                and str(e.ultima_calibracion).strip() != ""
            ):

                ultima = datetime.strptime(
                    e.ultima_calibracion,
                    "%Y-%m-%d"
                ).date()

                proximo = ultima + relativedelta(
                    months=e.frecuencia_metrologia
                )

                eventos.append({
                    "codigo": e.codigo,
                    "nombre": e.nombre,
                    "tipo": "Calibración",
                    "fecha": proximo.strftime("%Y-%m-%d"),
                    "ubicacion": e.ubicacion
                })

        except Exception as error:
            print("Error calibración:", error)

    # 🔎 FILTROS
    mes = request.args.get("mes")
    ubicacion = request.args.get("ubicacion")

    if mes:
        eventos = [
            evento for evento in eventos
            if evento["fecha"].startswith(mes)
        ]

    if ubicacion:
        eventos = [
            evento for evento in eventos
            if ubicacion.lower() in (evento["ubicacion"] or "").lower()
        ]

    eventos.sort(key=lambda x: x["fecha"])

    return render_template(
        "cronograma.html",
        eventos=eventos
    )

@app.route("/historial/<codigo>")
def historial(codigo):

    if "usuario" not in session:
        return redirect("/login")

    equipo = Equipo.query.filter_by(codigo=codigo).first()

    if not equipo:
        return "Equipo no encontrado"

    return render_template(
        "historial.html",
        equipo=equipo
    )

@app.route("/reporte/<codigo>")
def reporte(codigo):

    if "usuario" not in session:
        return redirect("/login")

    equipo = Equipo.query.filter_by(codigo=codigo).first()

    if not equipo:
        return "Equipo no encontrado"

    try:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.pagesizes import letter

        # 📁 carpeta reportes
        carpeta = "/tmp/reportes"
        os.makedirs(carpeta, exist_ok=True)

        # 🕒 nombre único (evita errores en servidor)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        archivo = f"reporte_{codigo}_{timestamp}.pdf"
        ruta = os.path.join(carpeta, archivo)

        # 📄 documento
        doc = SimpleDocTemplate(ruta, pagesize=letter)
        styles = getSampleStyleSheet()

        contenido = []

        # 🧾 TÍTULO
        contenido.append(Paragraph("<b>REPORTE BIOMÉDICO</b>", styles["Title"]))
        contenido.append(Spacer(1, 12))

        # 📊 DATOS DEL EQUIPO
        datos = [
            ("Código", equipo.codigo),
            ("Nombre", equipo.nombre),
            ("Marca", equipo.marca),
            ("Modelo", equipo.modelo),
            ("Serie", equipo.serie),
            ("Ubicación", equipo.ubicacion),
            ("Clase", equipo.clase),
            ("INVIMA", equipo.invima),
            ("Fecha compra", equipo.fecha_compra),
            ("Proveedor", equipo.proveedor),
            ("Fecha instalación", equipo.fecha_instalacion),
            ("Frecuencia mantenimiento (meses)", equipo.frecuencia_mantenimiento),
            ("Último mantenimiento", equipo.ultimo_mantenimiento),
            ("Metrología", equipo.metrologia),
            ("Frecuencia metrología (meses)", equipo.frecuencia_metrologia),
            ("Última calibración", equipo.ultima_calibracion),
            ("Observaciones", equipo.observaciones),
        ]

        for k, v in datos:
            contenido.append(
                Paragraph(f"<b>{k}:</b> {v if v else '-'}", styles["Normal"])
            )

        contenido.append(Spacer(1, 12))

        # 🧠 HISTORIAL (preparado para cuando lo migres a DB)
        if hasattr(equipo, "historiales") and equipo.historiales:
            contenido.append(Paragraph("<b>Historial</b>", styles["Heading2"]))
            contenido.append(Spacer(1, 8))

            for h in equipo.historiales:
                contenido.append(
                    Paragraph(f"{h.tipo} - {h.fecha}", styles["Normal"])
                )

        # 🏗 GENERAR PDF
        doc.build(contenido)

        # 📥 DESCARGA
        return send_from_directory(carpeta, archivo, as_attachment=True)

    except Exception as e:
        return f"Error al generar PDF: {str(e)}"

# ------------------ RUN ------------------

if __name__ == "__main__":

    with app.app_context():
        db.drop_all()
        db.create_all()

    app.run(debug=True)

