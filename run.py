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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///oportunidades.db'

db = SQLAlchemy(app)

# Modelo de Usuario
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(10), nullable=False, default='USER')

# Modelo de Oportunidad
class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
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

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/create_admin', methods=['GET', 'POST'])
def create_admin():
    if request.method == 'POST':
        username = request.form['username']
        if User.query.filter_by(username=username).first():
            return render_template('create_admin.html', error="Error: El nombre de usuario ya existe.")

        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password, user_type='ADMIN')
        db.session.add(new_user)
        db.session.commit()
        return "Admin user created successfully!"
    return render_template('create_admin.html')

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    
    # Verifica si el usuario tiene permisos de administrador
    if user.user_type != 'ADMIN':
        return "Access denied!"

    opportunities = Opportunity.query.all()
    
    # Obtener los usuarios para cada oportunidad
    for opportunity in opportunities:
        opportunity.user = User.query.get(opportunity.user_id)
    
    return render_template('admin.html', opportunities=opportunities)




@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('registro_oportunidades'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('registro_oportunidades'))

        return "Usuario o contraseña incorrectos. Intenta de nuevo."

    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro_oportunidades():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    vendedores = ["Vendedor 1", "Vendedor 2", "Vendedor 3"]
    if request.method == 'POST':
        user_id = session['user_id']
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
            user_id=user_id,
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

@app.route('/oportunidades')
def ver_oportunidades():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    
    if user.user_type == 'ADMIN':
        opportunities = Opportunity.query.all()
        
        # Obtener los usuarios para cada oportunidad
        for opportunity in opportunities:
            opportunity.user = User.query.get(opportunity.user_id)
            # Convertir la fecha de creación a la zona horaria de CDMX
            if opportunity.fecha_creacion:
                cdmx_tz = pytz.timezone('America/Mexico_City')
                opportunity.fecha_creacion = opportunity.fecha_creacion.replace(tzinfo=pytz.utc).astimezone(cdmx_tz)
        
        return render_template('admin.html', opportunities=opportunities)
    else:
        oportunidades = Opportunity.query.filter_by(user_id=user.id).all()

        cdmx_tz = pytz.timezone('America/Mexico_City')
        for oportunidad in oportunidades:
            if oportunidad.fecha_creacion:
                oportunidad.fecha_creacion = oportunidad.fecha_creacion.replace(tzinfo=pytz.utc).astimezone(cdmx_tz)
        
        return render_template('ver_oportunidades.html', oportunidades=oportunidades)


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_oportunidad(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    oportunidad = Opportunity.query.get_or_404(id)

    if request.method == 'POST':
        oportunidad.descripcion_estatus = request.form['descripcion_estatus']
        oportunidad.comentarios = request.form['comentarios']
        db.session.commit()
        return redirect(url_for('ver_oportunidades'))

    return render_template('editar.html', oportunidad=oportunidad)

@app.route('/exportar')
def exportar_oportunidades():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    if user.user_type == 'ADMIN':
        oportunidades = Opportunity.query.all()
    else:
        oportunidades = Opportunity.query.filter_by(user_id=user_id).all()

    output = StringIO()
    writer = csv.writer(output)

    # Cambiar el orden de las columnas
    writer.writerow([
        'ID', 'Fecha Creacion', 'Nombre Preventa', 'Nombre Oportunidad', 'Deal ID', 'Cliente', 'Vendedor', 'Producto',
        'Fecha Solicitud', 'Fecha Entrega', 'Estatus Preventa', 'Estatus Comercial', 'Comentarios'
    ])

    for oportunidad in oportunidades:
        nombre_preventa = User.query.get(oportunidad.user_id).username if user.user_type == 'ADMIN' else ''

        writer.writerow([
            oportunidad.id,
            oportunidad.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S'),
            nombre_preventa,
            oportunidad.nombre,
            oportunidad.deal_id,
            oportunidad.cliente,
            oportunidad.vendedor,
            oportunidad.producto,
            oportunidad.fecha_solicitud.strftime('%Y-%m-%d'),
            oportunidad.fecha_entrega.strftime('%Y-%m-%d'),
            oportunidad.estatus,
            oportunidad.descripcion_estatus,
            oportunidad.comentarios
        ])

    output.seek(0)

    fecha_hora = datetime.now().strftime('%d-%m-%Y_%H-%M')
    nombre_archivo = f'Oportunidades2025_{fecha_hora}.csv'

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename={nombre_archivo}"}
    )

@app.route('/detalles/<int:id>')
def detalles_oportunidad(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    oportunidad = Opportunity.query.get_or_404(id)

    return render_template('detalles_oportunidad.html', oportunidad=oportunidad)


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    if not os.path.exists('users'):
        os.makedirs('users')

    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username="ivan").first():
            testuser = User(username="ivan", password=generate_password_hash("ivan123", method='pbkdf2:sha256'), user_type='ADMIN')
            db.session.add(testuser)
            db.session.commit()

        if not User.query.filter_by(username="userfake").first():
            userfake = User(username="userfake", password=generate_password_hash("fakepassword", method='pbkdf2:sha256'))
            db.session.add(userfake)
            db.session.commit()
        
        if not User.query.filter_by(username="Juan Perez").first():
            juanperez = User(username="Juan Perez", password=generate_password_hash("juanperez123", method='pbkdf2:sha256'))
            db.session.add(juanperez)
            db.session.commit()

    app.run(debug=True)