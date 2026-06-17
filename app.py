import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "clave-insegura-solo-para-desarrollo")

database_url = os.environ.get("DATABASE_URL", "sqlite:///local.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- CONFIGURACIÓN DE FLASK-LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Por favor inicia sesión para acceder a esta página."


# --- MODELO DE USUARIO ADMIN ---
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# --- MODELO MENSAJES DE CONTACTO ---
class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)


# --- RUTAS PÚBLICAS ---

@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/contacto", methods=["POST"])
def contacto():
    nombre = request.form.get("nombre", "").strip()
    email = request.form.get("email", "").strip()
    contenido = request.form.get("contenido", "").strip()

    if not nombre or not email or not contenido:
        flash("Por favor rellena todos los campos.", "error")
        return redirect(url_for("inicio"))

    nuevo_mensaje = Mensaje(nombre=nombre, email=email, contenido=contenido)
    db.session.add(nuevo_mensaje)
    db.session.commit()

    flash("¡Gracias! Hemos recibido tu mensaje.", "success")
    return redirect(url_for("inicio"))


# --- AUTENTICACIÓN ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        usuario = Usuario.query.filter_by(email=email).first()

        # Mensaje genérico tanto si el email no existe como si la contraseña
        # es incorrecta, para no revelar a un atacante si ese email existe.
        if usuario is None or not usuario.check_password(password):
            flash("Email o contraseña incorrectos.", "error")
            return redirect(url_for("login"))

        login_user(usuario)
        return redirect(url_for("admin"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# --- ZONA PROTEGIDA ---

@app.route("/negro")
@login_required
def admin():
    mensajes = Mensaje.query.order_by(Mensaje.fecha.desc()).all()
    return render_template("admin.html", mensajes=mensajes)


with app.app_context():
    db.create_all()


# Comando de terminal para crear el primer usuario admin.
# Se ejecuta así: flask create-admin
# NUNCA se expone como ruta web pública.
@app.cli.command("create-admin")
def create_admin():
    import getpass

    email = input("Email del admin: ").strip().lower()
    password = getpass.getpass("Contraseña: ")
    password_confirm = getpass.getpass("Confirma la contraseña: ")

    if password != password_confirm:
        print("Las contraseñas no coinciden.")
        return

    if Usuario.query.filter_by(email=email).first():
        print(f"Ya existe un usuario con el email {email}.")
        return

    nuevo_admin = Usuario(email=email)
    nuevo_admin.set_password(password)
    db.session.add(nuevo_admin)
    db.session.commit()
    print(f"Usuario admin '{email}' creado correctamente.")


if __name__ == "__main__":
    app.run(debug=True)
