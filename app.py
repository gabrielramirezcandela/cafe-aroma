import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Cargar variables de entorno desde .env (en local)
load_dotenv()

app = Flask(__name__)

# SECRET_KEY se usa para sesiones, mensajes flash, formularios seguros, etc.
# En producción SIEMPRE debe venir de variable de entorno, nunca escrita en el código.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "clave-insegura-solo-para-desarrollo")

# Configuración de la base de datos.
# Render nos dará una URL de PostgreSQL en producción a través de la variable DATABASE_URL.
# En local, si no existe esa variable, usamos SQLite (un simple archivo .db) para no complicarnos.
database_url = os.environ.get("DATABASE_URL", "sqlite:///local.db")

# Render entrega la URL con el prefijo "postgres://" pero SQLAlchemy moderno necesita "postgresql://"
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# --- MODELO DE BASE DE DATOS ---
class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Mensaje {self.id} de {self.nombre}>"


# --- RUTAS ---

@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/contacto", methods=["POST"])
def contacto():
    nombre = request.form.get("nombre", "").strip()
    email = request.form.get("email", "").strip()
    contenido = request.form.get("contenido", "").strip()

    # Validación básica en servidor (nunca confíes solo en validación del navegador)
    if not nombre or not email or not contenido:
        flash("Por favor rellena todos los campos.", "error")
        return redirect(url_for("inicio"))

    nuevo_mensaje = Mensaje(nombre=nombre, email=email, contenido=contenido)
    db.session.add(nuevo_mensaje)
    db.session.commit()

    flash("¡Gracias! Hemos recibido tu mensaje.", "success")
    return redirect(url_for("inicio"))


@app.route("/admin")
def admin():
    # Esto es deliberadamente simple para el ejemplo.
    # En un proyecto real esta ruta debe estar protegida con login (lo veremos más adelante).
    mensajes = Mensaje.query.order_by(Mensaje.fecha.desc()).all()
    return render_template("admin.html", mensajes=mensajes)


# Crea las tablas de la base de datos si no existen todavía
with app.app_context():
    db.create_all()


if __name__ == "__main__":
    # debug=True SOLO en local. En producción Gunicorn ejecuta la app, esto no se usa.
    app.run(debug=True)
