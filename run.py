from flask import Flask, render_template, request, redirect, url_for, session, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
import csv
from io import StringIO
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Inicializar Flask
app = Flask(__name__)
app.secret_key = 'secret_key'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Esta es la base de datos global de usuarios (usuario y autenticación)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///oportunidades.db'
db = SQLAlchemy(app)

# Modelo de Usuario
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Modelo de Oportunidad (definido sin modificar)
class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    cliente = db.Column(db.String(100), nullable=False)
    vendedor = db.Column(db.String(100), nullable=False)
    producto = db.Column(db.String(100), nullable=False)
    fecha_solicitud = db.Column(db.Date, nullable=False)
    fecha_entrega = db.Column(db.Date, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    estatus = db.Column(db.String(50), nullable=False, default='En Proceso')
    descripcion_estatus = db.Column(db.String(500), nullable=True)
    comentarios = db.Column(db.String(500), nullable=True)
    deal_id = db.Column(db.String(100), nullable=True)

# Ruta principal para redirigir al login
@app.route('/')
def home():
    return redirect(url_for('login'))

# Ruta para login
# Ruta para login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('registro_oportunidades'))  # Si ya está logueado, redirige al registro de oportunidades

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()  # Buscar usuario en la base de datos

        # Verificar si el usuario existe y si la contraseña es correcta
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id  # Guardar el ID del usuario en la sesión

            # Cambiar la base de datos a la del usuario
            user_db_path = f'users/{username}_db.sqlite'
            
            # Establecer la URI de la base de datos antes de la inicialización de db
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{user_db_path}'
            db.session.remove()  # Eliminar la sesión actual
            db.engine.dispose()  # Liberar el motor actual de SQLAlchemy
            
            # Crear las tablas si no existen en la base de datos del usuario
            if not os.path.exists(user_db_path):
                db.create_all()  # Crear las tablas para este usuario

            return redirect(url_for('registro_oportunidades'))  # Redirigir a la página de registro de oportunidades
        else:
            # Si las credenciales son incorrectas
            return "Usuario o contraseña incorrectos. Intenta de nuevo."

    return render_template('login.html')  # Mostrar el formulario de login



# Ruta para registrar una oportunidad
@app.route('/registro', methods=['GET', 'POST'])
def registro_oportunidades():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    vendedores = ["Vendedor 1", "Vendedor 2", "Vendedor 3"]
    if request.method == 'POST':
        nombre = request.form['nombre']
        cliente = request.form['cliente']
        vendedor = request.form['vendedor']
        producto = request.form['producto']
        fecha_solicitud = request.form['fecha_solicitud']
        fecha_entrega = request.form['fecha_entrega']
        estatus = request.form['estatus_comercial']
        descripcion_estatus = request.form['descripcion_estatus']
        comentarios = request.form['comentarios']
        deal_id = request.form['deal_id']

        nueva_oportunidad = Opportunity(
            nombre=nombre,
            cliente=cliente,
            vendedor=vendedor,
            producto=producto,
            fecha_solicitud=datetime.strptime(fecha_solicitud, '%Y-%m-%d'),
            fecha_entrega=datetime.strptime(fecha_entrega, '%Y-%m-%d'),
            estatus=estatus,
            descripcion_estatus=descripcion_estatus,
            comentarios=comentarios,
            deal_id=deal_id
        )
        db.session.add(nueva_oportunidad)
        db.session.commit()
        return redirect(url_for('registro_oportunidades'))

    return render_template('registro.html', vendedores=vendedores)

# Ruta para ver todas las oportunidades registradas
@app.route('/oportunidades')
def ver_oportunidades():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Obtener todas las oportunidades de la base de datos
    oportunidades = Opportunity.query.all()

    # Zona horaria de CDMX
    cdmx_tz = pytz.timezone('America/Mexico_City')

    # Convertir la fecha de creación a la zona horaria de CDMX
    for oportunidad in oportunidades:
        if isinstance(oportunidad.fecha_creacion, str):
            oportunidad.fecha_creacion = datetime.strptime(oportunidad.fecha_creacion, '%Y-%m-%d %H:%M:%S')
        if oportunidad.fecha_creacion:
            oportunidad.fecha_creacion = oportunidad.fecha_creacion.replace(tzinfo=pytz.utc).astimezone(cdmx_tz)

    return render_template('ver_oportunidades.html', oportunidades=oportunidades)

# Ruta para exportar oportunidades a un archivo CSV
@app.route('/exportar')
def exportar_oportunidades():
    # Obtener todas las oportunidades de la base de datos
    oportunidades = Opportunity.query.all()

    # Crear un objeto StringIO para escribir el CSV en memoria
    output = StringIO()
    writer = csv.writer(output)

    # Escribir el encabezado del CSV
    writer.writerow([ 
        'Fecha Creación', 'ID', 'Nombre', 'Cliente', 'Vendedor', 'Producto',
        'Fecha Solicitud', 'Fecha Entrega', 'Estatus Preventa', 'Descripción del Estatus Comercial', 
        'Comentarios', 'DEAL Id'
    ])

    # Escribir los datos de las oportunidades
    for oportunidad in oportunidades:
        writer.writerow([ 
            oportunidad.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S'),
            oportunidad.id,
            oportunidad.nombre,
            oportunidad.cliente,
            oportunidad.vendedor,
            oportunidad.producto,
            oportunidad.fecha_solicitud.strftime('%Y-%m-%d'),
            oportunidad.fecha_entrega.strftime('%Y-%m-%d'),
            oportunidad.estatus,
            oportunidad.descripcion_estatus,
            oportunidad.comentarios,
            oportunidad.deal_id
        ])

    # Mover el cursor al inicio del StringIO
    output.seek(0)

    # Crear la respuesta de archivo CSV para la descarga
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=oportunidades.csv"}
    )

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Crear el directorio de usuarios si no existe
    if not os.path.exists('users'):
        os.makedirs('users')

    # Inicializar la base de datos global para usuarios
    with app.app_context():
        db.create_all()  # Inicializa las tablas de la base de datos

        # Crear los usuarios predeterminados si no existen
        if not User.query.filter_by(username="testuser").first():
            testuser = User(username="testuser", password=generate_password_hash("testpassword"))
            db.session.add(testuser)
            db.session.commit()

        if not User.query.filter_by(username="userfake").first():
            userfake = User(username="userfake", password=generate_password_hash("fakepassword"))
            db.session.add(userfake)
            db.session.commit()

    app.run(debug=True)
