import os
import socket
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, make_response
from functools import wraps
import qrcode
from io import BytesIO
import base64
from fpdf import FPDF
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_mensajes_flash'

# Configuración de base de datos
# Usa la variable DATABASE_URL que Render inyecta automáticamente
# Si no existe (local), usa SQLite para pruebas
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    # Para pruebas locales, usa SQLite (no necesitas PostgreSQL instalado)
    database_url = 'sqlite:///asistentes.db'
else:
    # Render usa 'postgres://', pero SQLAlchemy requiere 'postgresql://'
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# =====================================================
# Modelo de datos
# =====================================================
class Asistente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    conferencia_id = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.String(50))  # fecha_mostrar
    titulo = db.Column(db.String(500))
    hora_inicio = db.Column(db.String(50))
    entrada = db.Column(db.String(50), default='')
    salida = db.Column(db.String(50), default='')
    salida_activada = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'nombre': self.nombre,
            'email': self.email,
            'conferencia_id': self.conferencia_id,
            'fecha': self.fecha,
            'titulo': self.titulo,
            'hora_inicio': self.hora_inicio,
            'entrada': self.entrada or '',
            'salida': self.salida or '',
            'salida_activada': self.salida_activada
        }

# Crear tablas (solo una vez)
with app.app_context():
    db.create_all()

# =====================================================
# CONFERENCIAS (igual que antes)
# =====================================================
CONFERENCIAS = [
    {'id': 1, 'fecha': '2026-05-18', 'fecha_mostrar': '18 de mayo', 'hora': '12:00', 'titulo': 'Aprovechamiento energético de matrices fisiológicas mediante plataformas microfluídicas electroquímicas'},
    {'id': 2, 'fecha': '2026-05-19', 'fecha_mostrar': '19 de mayo', 'hora': '15:00', 'titulo': 'Industria 4.0 y 5.0'},
    {'id': 3, 'fecha': '2026-05-19', 'fecha_mostrar': '19 de mayo', 'hora': '16:00', 'titulo': 'Síntesis de nanopartículas de Óxidos metálicos nanoestructurados y su aplicación fotocatalítica en el tratamiento de agua'},
    {'id': 4, 'fecha': '2026-05-20', 'fecha_mostrar': '20 de mayo', 'hora': '15:00', 'titulo': 'Síntesis verde: una ruta sostenible para la obtención de nanomateriales'},
    {'id': 5, 'fecha': '2026-05-20', 'fecha_mostrar': '20 de mayo', 'hora': '16:00', 'titulo': 'La cadena de valor de los semiconductores en el IPN ¿Cuál es la oportunidad real?'},
    {'id': 6, 'fecha': '2026-05-21', 'fecha_mostrar': '21 de mayo', 'hora': '11:00', 'titulo': 'Polímeros controlados e Hidrogeles'}
]

# =====================================================
# Funciones auxiliares (adaptadas a BD)
# =====================================================
def obtener_asistente(email, conferencia_id):
    return Asistente.query.filter_by(email=email, conferencia_id=conferencia_id).first()

# =====================================================
# Generación de constancias (igual)
# =====================================================
# (Aquí van las mismas funciones generar_constancia_con_fondo y generar_constancia_simple)
# Para no alargar, copia las que ya tienes desde la versión anterior.
# Voy a ponerlas más abajo en el código completo.

# =====================================================
# RUTAS
# =====================================================

@app.route('/')
def index():
    # Usamos la URL pública configurable (para local o producción)
    base_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:5000')
    qr_codes = []
    for conf in CONFERENCIAS:
        url = f'{base_url}/registro/{conf["id"]}'
        qr = qrcode.make(url)
        buffered = BytesIO()
        qr.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        qr_codes.append({
            'id': conf['id'],
            'fecha_mostrar': conf['fecha_mostrar'],
            'hora': conf['hora'],
            'titulo': conf['titulo'],
            'img': img_str,
            'url': url
        })
    return render_template('index.html', qr_codes=qr_codes, local_ip="render")

@app.route('/registro/<int:conferencia_id>', methods=['GET', 'POST'])
def registro_dia(conferencia_id):
    conferencia = next((c for c in CONFERENCIAS if c['id'] == conferencia_id), None)
    if conferencia is None:
        return "Conferencia no encontrada", 404

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        tipo = request.form.get('tipo')
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        asistente = obtener_asistente(email, conferencia_id)

        if tipo == 'entrada':
            if asistente and asistente.entrada:
                flash('❌ Ya registraste entrada para esta conferencia.', 'danger')
                return redirect(url_for('registro_dia', conferencia_id=conferencia_id))
            if asistente is None:
                nuevo = Asistente(
                    nombre=nombre,
                    email=email,
                    conferencia_id=conferencia_id,
                    fecha=conferencia['fecha_mostrar'],
                    titulo=conferencia['titulo'],
                    hora_inicio=ahora,
                    entrada=ahora,
                    salida='',
                    salida_activada=False
                )
                db.session.add(nuevo)
            else:
                asistente.entrada = ahora
                asistente.hora_inicio = ahora
                asistente.salida_activada = False
            db.session.commit()
            flash(f'✅ ENTRADA registrada para {nombre}', 'success')

        elif tipo == 'salida':
            if not asistente or not asistente.entrada:
                flash('❌ No puedes registrar salida sin haber registrado entrada primero.', 'danger')
                return redirect(url_for('registro_dia', conferencia_id=conferencia_id))
            if asistente.salida:
                flash('❌ Ya registraste salida para esta conferencia.', 'danger')
                return redirect(url_for('registro_dia', conferencia_id=conferencia_id))
            if not asistente.salida_activada:
                flash('🔒 La salida aún no está habilitada. Espera a que el organizador la active.', 'warning')
                return redirect(url_for('registro_dia', conferencia_id=conferencia_id))
            asistente.salida = ahora
            db.session.commit()
            flash(f'✅ SALIDA registrada para {nombre}', 'success')

        return redirect(url_for('registro_dia', conferencia_id=conferencia_id))

    return render_template('registro.html', conferencia=conferencia)

# Rutas de administración (protegidas)
def check_auth(username, password):
    return username == 'admin' and password == 'admin123'

def authenticate():
    return ('Unauthorized', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/admin')
@requires_auth
def admin():
    pendientes = Asistente.query.filter(Asistente.entrada != '', Asistente.salida == '').all()
    registros = [a.to_dict() for a in pendientes]
    # Para la vista, necesitamos también las conferencias completas
    return render_template('admin.html', registros=registros, conferencias=CONFERENCIAS)

@app.route('/admin/activar/<int:id>')
@requires_auth
def activar_salida(id):
    asistente = Asistente.query.get(id)
    if asistente and not asistente.salida:
        asistente.salida_activada = True
        db.session.commit()
        flash(f'✅ Salida ACTIVADA para {asistente.nombre}', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/desactivar/<int:id>')
@requires_auth
def desactivar_salida(id):
    asistente = Asistente.query.get(id)
    if asistente and not asistente.salida:
        asistente.salida_activada = False
        db.session.commit()
        flash(f'🔒 Salida DESACTIVADA para {asistente.nombre}', 'warning')
    return redirect(url_for('admin'))

@app.route('/admin/activar_todos/<int:conferencia_id>')
@requires_auth
def activar_todos(conferencia_id):
    asistentes = Asistente.query.filter(Asistente.conferencia_id == conferencia_id, Asistente.entrada != '', Asistente.salida == '').all()
    for a in asistentes:
        a.salida_activada = True
    db.session.commit()
    flash('✅ Salida ACTIVADA para TODOS los asistentes', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/desactivar_todos/<int:conferencia_id>')
@requires_auth
def desactivar_todos(conferencia_id):
    asistentes = Asistente.query.filter(Asistente.conferencia_id == conferencia_id, Asistente.entrada != '', Asistente.salida == '').all()
    for a in asistentes:
        a.salida_activada = False
    db.session.commit()
    flash('🔒 Salida DESACTIVADA para TODOS los asistentes', 'warning')
    return redirect(url_for('admin'))

@app.route('/ver_registros')
@requires_auth
def ver_registros():
    todos = Asistente.query.all()
    registros = [a.to_dict() for a in todos]
    return render_template('ver_registros.html', registros=registros)

# Rutas de constancia (igual que antes, requieren las funciones de generación de PDF)
# ... copiar las funciones generar_constancia_con_fondo y generar_constancia_simple desde tu código original.
# También las rutas /constancia, /constancia-qr, /descargar-constancia-qr.

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
