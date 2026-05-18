import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, make_response
from functools import wraps
import qrcode
from io import BytesIO
import base64
from fpdf import FPDF
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_mensajes_flash'

# =====================================================
# CONFIGURACIÓN DE BASE DE DATOS
# =====================================================
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    database_url = 'sqlite:///asistentes.db'
else:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# =====================================================
# MODELO DE DATOS
# =====================================================
class Asistente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    conferencia_id = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.String(50))
    titulo = db.Column(db.String(500))
    hora_inicio = db.Column(db.String(50))
    entrada = db.Column(db.String(50), default='')
    salida = db.Column(db.String(50), default='')
    salida_activada = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
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

with app.app_context():
    db.create_all()

# =====================================================
# CONFERENCIAS
# =====================================================
CONFERENCIAS = [
    {'id': 1, 'fecha': '2026-05-18', 'fecha_mostrar': '18 de mayo', 'hora': '12:00', 'titulo': 'Aprovechamiento energético de matrices fisiológicas mediante plataformas microfluídicas electroquímicas'},
    {'id': 2, 'fecha': '2026-05-19', 'fecha_mostrar': '19 de mayo', 'hora': '15:00', 'titulo': 'Industria 4.0 y 5.0'},
    {'id': 3, 'fecha': '2026-05-19', 'fecha_mostrar': '19 de mayo', 'hora': '16:00', 'titulo': 'Síntesis de nanopartículas de Óxidos metálicos nanoestructurados y su aplicación fotocatalítica en el tratamiento de agua'},
    {'id': 4, 'fecha': '2026-05-20', 'fecha_mostrar': '20 de mayo', 'hora': '15:00', 'titulo': 'Síntesis verde: una ruta sostenible para la obtención de nanomateriales'},
    {'id': 5, 'fecha': '2026-05-20', 'fecha_mostrar': '20 de mayo', 'hora': '16:00', 'titulo': 'La cadena de valor de los semiconductores en el IPN ¿Cuál es la oportunidad real?'},
    {'id': 6, 'fecha': '2026-05-21', 'fecha_mostrar': '21 de mayo', 'hora': '11:00', 'titulo': 'Polímeros controlados e Hidrogeles'}
]

def obtener_asistente(email, conferencia_id):
    return Asistente.query.filter_by(email=email, conferencia_id=conferencia_id).first()

# =====================================================
# GENERACIÓN DE CONSTANCIAS
# =====================================================
def generar_constancia_con_fondo(fila):
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.colors import HexColor
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        return generar_constancia_simple(fila)
    
    fondo_path = "fondo_constancia.pdf"
    if not os.path.exists(fondo_path):
        return generar_constancia_simple(fila)
    
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica-Bold", 28)
    can.setFillColor(HexColor('#8B0000'))
    can.drawCentredString(306, 380, fila['nombre'])
    can.setFont("Helvetica-Bold", 12)
    can.setFillColor(HexColor('#000000'))
    titulo = fila['titulo']
    if len(titulo) > 65:
        can.drawCentredString(306, 290, titulo[:65])
        can.drawCentredString(306, 272, titulo[65:])
    else:
        can.drawCentredString(306, 290, titulo)
    can.setFont("Helvetica", 11)
    can.setFillColor(HexColor('#333333'))
    can.drawCentredString(306, 240, f"Fecha: {fila['fecha']}")
    can.save()
    reader = PdfReader(fondo_path)
    writer = PdfWriter()
    packet.seek(0)
    overlay = PdfReader(packet)
    page = reader.pages[0]
    page.merge_page(overlay.pages[0])
    writer.add_page(page)
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output

def generar_constancia_simple(fila):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 20, "CONSTANCIA DE PARTICIPACIÓN", ln=True, align='C')
    pdf.ln(20)
    pdf.set_font("Arial", '', 14)
    pdf.cell(0, 10, "Se otorga a:", ln=True, align='C')
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 15, fila['nombre'], ln=True, align='C')
    pdf.set_font("Arial", '', 14)
    pdf.cell(0, 10, "Por su participación en la conferencia:", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.multi_cell(0, 8, fila['titulo'], align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Fecha: {fila['fecha']}", ln=True, align='C')
    pdf.ln(15)
    pdf.cell(0, 10, "Firma", ln=True, align='R')
    temp_pdf = "temp_constancia.pdf"
    pdf.output(temp_pdf)
    with open(temp_pdf, 'rb') as f:
        pdf_data = f.read()
    os.remove(temp_pdf)
    return BytesIO(pdf_data)

# =====================================================
# RUTAS
# =====================================================
@app.route('/')
def index():
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
    return render_template('admin.html', registros=registros, conferencias=CONFERENCIAS)

@app.route('/admin/activar/<int:id>')
@requires_auth
def activar_salida(id):
    a = Asistente.query.get(id)
    if a and not a.salida:
        a.salida_activada = True
        db.session.commit()
        flash(f'✅ Salida ACTIVADA para {a.nombre}', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/desactivar/<int:id>')
@requires_auth
def desactivar_salida(id):
    a = Asistente.query.get(id)
    if a and not a.salida:
        a.salida_activada = False
        db.session.commit()
        flash(f'🔒 Salida DESACTIVADA para {a.nombre}', 'warning')
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

@app.route('/constancia', methods=['GET', 'POST'])
def constancia():
    if request.method == 'POST':
        email = request.form.get('email')
        conferencia_id = int(request.form.get('conferencia_id'))
        asistente = obtener_asistente(email, conferencia_id)
        if not asistente:
            flash('No se encontró ningún registro con ese email.', 'danger')
            return redirect(url_for('constancia'))
        if not asistente.entrada or not asistente.salida:
            flash('❌ No puedes generar constancia porque faltan entrada o salida.', 'danger')
            return redirect(url_for('constancia'))
        pdf_file = generar_constancia_con_fondo(asistente.to_dict())
        nombre_limpio = asistente.nombre.replace(' ', '_').replace('/', '_')
        return send_file(pdf_file, as_attachment=True,
                         download_name=f"constancia_{nombre_limpio}.pdf",
                         mimetype='application/pdf')
    return render_template('constancia.html', conferencias=CONFERENCIAS)

@app.route('/constancia-qr', methods=['GET'])
def constancia_qr():
    return render_template('constancia_qr.html', conferencias=CONFERENCIAS)

@app.route('/descargar-constancia-qr', methods=['POST'])
def descargar_constancia_qr():
    email = request.form.get('email')
    conferencia_id = int(request.form.get('conferencia_id'))
    asistente = obtener_asistente(email, conferencia_id)
    if not asistente:
        flash('No se encontró ningún registro con ese correo para esa conferencia.', 'error')
        return redirect(url_for('constancia_qr'))
    if not asistente.entrada or not asistente.salida:
        flash('❌ Aún no puedes generar la constancia. Debes tener entrada y salida registradas.', 'error')
        return redirect(url_for('constancia_qr'))
    try:
        pdf_file = generar_constancia_con_fondo(asistente.to_dict())
    except:
        pdf_file = generar_constancia_simple(asistente.to_dict())
    nombre_limpio = asistente.nombre.replace(' ', '_').replace('/', '_')
    return send_file(pdf_file, as_attachment=True,
                     download_name=f"constancia_{nombre_limpio}.pdf",
                     mimetype='application/pdf')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
    app.run(debug=False, host='0.0.0.0', port=port)
