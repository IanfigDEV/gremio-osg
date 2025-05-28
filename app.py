from flask import render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'secreto'
import os
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'banco.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matricula = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    senha = db.Column(db.String(100), nullable=False)

@app.route("/")
def index():
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        matricula = request.form["matricula"]
        nome = request.form["nome"]
        senha = request.form["senha"]

        # Verifica se matrícula já está cadastrada
        if Usuario.query.filter_by(matricula=matricula).first():
            return "Usuário já existe."

        senha_hash = generate_password_hash(senha)

        novo_usuario = Usuario(matricula=matricula, nome=nome, senha=senha_hash)
        db.session.add(novo_usuario)
        db.session.commit()
        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        matricula = request.form["matricula"]
        senha = request.form["senha"]

        usuario = Usuario.query.filter_by(matricula=matricula).first()
        if usuario and check_password_hash(usuario.senha, senha):
            session["usuario_id"] = usuario.id
            return redirect("/dashboard")
        else:
            erro = "Usuário ou senha inválidos."

    return render_template("login.html", erro=erro)

@app.route("/dashboard")
def dashboard():
    if "usuario_id" not in session:
        return redirect("/login")

    usuario = Usuario.query.get(session["usuario_id"])

    if not usuario:
        # Caso o usuário não exista no banco, desloga e redireciona
        session.pop("usuario_id", None)
        return redirect("/login")

    return f"Bem-vindo, {usuario.nome}!"
    
@app.route("/logout")
def logout():
    session.pop("usuario_id", None)
    return redirect("/login")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=3000, debug=True)

