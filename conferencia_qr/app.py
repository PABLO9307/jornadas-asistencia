import os
import socket
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, make_response
from functools import wraps
import qrcode
from io import BytesIO
import base64
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_mensajes_flash'

EXCEL_FILE = 'asistentes.xlsx'

# =====================================================
# Obtener IP local de red
# =====================================================
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

# =====================================================
# Autenticación básica para rutas de administrador
# =====================================================
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

# =====================================================
# CONFERENCIAS
# =====================================================
CONFERENCIAS = [
    {
        'id': 1,
        'fecha': '2026-05-18',
        'fecha_mostrar': '18 de mayo',
        'hora': '12:00',
        'titulo': 'Aprovechamiento energético de matrices fisiológicas mediante plataformas microfluídicas electroquímicas'
    },
    {
        'id': 2,
        'fecha': '2026-05-19',
        'fecha_mostrar': '19 de mayo',
        'hora': '15:00',
        'titulo': 'Industria 4.0 y 5.0'
    },
    {
        'id': 3,
        'fecha': '2026-05-19',
        'fecha_mostrar': '19 de mayo',
        'hora': '16:00',
        'titulo': 'Síntesis de nanopartículas de Óxidos metálicos nanoestructurados y su aplicación fotocatalítica en el tratamiento de agua'
    },
    {
        'id': 4,
        'fecha': '2026-05-20',
        'fecha_mostrar': '20 de mayo',
        'hora': '15:00',
        'titulo': 'Síntesis verde: una ruta sostenible para la obtención de nanomateriales'
    },
    {
        'id': 5,
        'fecha': '2026-05-20',
        'fecha_mostrar': '20 de mayo',
        'hora': '16:00',
        'titulo': 'La cadena de valor de los semiconductores en el IPN ¿Cuál es la oportunidad real?'
    },
    {
        'id': 6,
        'fecha': '2026-05-21',
        'fecha_mostrar': '21 de mayo',
        'hora': '11:00',
        'titulo': 'Polímeros controlados e Hidrogeles'
    }
]

# Inicializar archivo Excel
def init_excel():
    if not os.path.exists(EXCEL_FILE):
        df = pd.DataFrame(columns=['nombre', 'email', 'conferencia_id', 'fecha', 'titulo', 'hora_inicio', 'entrada', 'salida', 'salida_activada', 'entrada_activada'])
        df['entrada'] = df['entrada'].astype(object)
        df['salida'] = df['salida'].astype(object)
        df['salida_activada'] = False
        df['entrada_activada'] = True  # Por defecto activada
        df.to_excel(EXCEL_FILE, index=False)

init_excel()

def leer_excel():
    df = pd.read_excel(EXCEL_FILE, dtype={'entrada': str, 'salida': str})
    df['entrada'] = df['entrada'].fillna('')
    df['salida'] = df['salida'].fillna('')
    if 'salida_activada' not in df.columns:
        df['salida_activada'] = False
    else:
        df['salida_activada'] = df['salida_activada'].fillna(False)
    if 'entrada_activada' not in df.columns:
        df['entrada_activada'] = True
    else:
        df['entrada_activada'] = df['entrada_activada'].fillna(True)
    return df

def guardar_excel(df):
    df.to_excel(EXCEL_FILE, index=False)

def obtener_fila_asistente(df, email, conferencia_id):
    mascara = (df['email'].str.lower() == email.lower()) & (df['conferencia_id'] == conferencia_id)
    indices = df[mascara].index
    if len(indices) > 0:
        return indices[0], df.loc[indices[0]]
    return None, None

# =====================================================
# GENERACIÓN DE CONSTANCIAS CON FONDO (SIN HORAS)
# =====================================================

def generar_constancia_con_fondo(fila):
    """Constancia con fondo personalizado - SIN horas"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.colors import HexColor
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        return generar_constancia_simple(fila)
    
    fondo_path = "fondo_constancia.pdf"
    if not os.path.exists(fondo_path):
        print("No se encontró fondo_constancia.pdf, usando versión simple")
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
    """Constancia simple SIN horas (respaldo)"""
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
# RUTAS DE LA APLICACIÓN
# =====================================================

@app.route('/')
def index():
    local_ip = get_local_ip()
    base_url = f'http://{local_ip}:5000'
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
    return render_template('index.html', qr_codes=qr_codes, local_ip=local_ip)

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

        df = leer_excel()
        indice, fila = obtener_fila_asistente(df, email, conferencia_id)

        if tipo == 'entrada':
            # Verificar si la entrada está activada por el admin
            if not df.at[indice, 'entrada_activada'] if indice is not None else True:
                flash('🔒 La entrada aún no está habilitada. Espera a que el organizador la active.', 'warning')
                return redirect(url_for('registro_dia', conferencia_id=conferencia_id))
            
            if fila is not None and fila['entrada'] != '':
                flash('❌ Ya registraste entrada para esta conferencia.', 'danger')
                return redirect(url_for('registro_dia', conferencia_id=conferencia_id))
            if fila is None:
                nueva_fila = pd.DataFrame([{
                    'nombre': nombre,
                    'email': email,
                    'conferencia_id': conferencia_id,
                    'fecha': conferencia['fecha_mostrar'],
                    'titulo': conferencia['titulo'],
                    'hora_inicio': ahora,
                    'entrada': ahora,
                    'salida': '',
                    'salida_activada': False,
                    'entrada_activada': True
                }])
                df = pd.concat([df, nueva_fila], ignore_index=True)
            else:
                df.at[indice, 'entrada'] = ahora
                df.at[indice, 'hora_inicio'] = ahora
            guardar_excel(df)
            flash(f'✅ ENTRADA registrada para {nombre}', 'success')

        elif tipo == 'salida':
            if fila is None or fila['entrada'] == '':
                flash('❌ No puedes registrar salida sin haber registrado entrada primero.', 'danger')
                return redirect(url_for('registro_dia', conferencia_id=conferencia_id))
            if fila['salida'] != '':
                flash('❌ Ya registraste salida para esta conferencia.', 'danger')
                return redirect(url_for('registro_dia', conferencia_id=conferencia_id))
            if not fila['salida_activada']:
                flash('🔒 La salida aún no está habilitada. Espera a que el organizador la active.', 'warning')
                return redirect(url_for('registro_dia', conferencia_id=conferencia_id))
            df.at[indice, 'salida'] = ahora
            guardar_excel(df)
            flash(f'✅ SALIDA registrada para {nombre}', 'success')

        return redirect(url_for('registro_dia', conferencia_id=conferencia_id))

    return render_template('registro.html', conferencia=conferencia)

# Rutas protegidas con autenticación
@app.route('/admin')
@requires_auth
def admin():
    df = leer_excel()
    pendientes = df[(df['entrada'] != '') & (df['salida'] == '')]
    registros = pendientes.to_dict('records')
    return render_template('admin.html', registros=registros, conferencias=CONFERENCIAS)

# Rutas para SALIDA
@app.route('/admin/activar/<int:indice>')
@requires_auth
def activar_salida(indice):
    df = leer_excel()
    if indice < len(df):
        df.at[indice, 'salida_activada'] = True
        guardar_excel(df)
        flash(f'✅ Salida ACTIVADA para {df.at[indice, "nombre"]}', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/desactivar/<int:indice>')
@requires_auth
def desactivar_salida(indice):
    df = leer_excel()
    if indice < len(df):
        df.at[indice, 'salida_activada'] = False
        guardar_excel(df)
        flash(f'🔒 Salida DESACTIVADA para {df.at[indice, "nombre"]}', 'warning')
    return redirect(url_for('admin'))

@app.route('/admin/activar_todos/<int:conferencia_id>')
@requires_auth
def activar_todos(conferencia_id):
    df = leer_excel()
    mascara = (df['conferencia_id'] == conferencia_id) & (df['entrada'] != '') & (df['salida'] == '')
    df.loc[mascara, 'salida_activada'] = True
    guardar_excel(df)
    flash('✅ Salida ACTIVADA para TODOS los asistentes', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/desactivar_todos/<int:conferencia_id>')
@requires_auth
def desactivar_todos(conferencia_id):
    df = leer_excel()
    mascara = (df['conferencia_id'] == conferencia_id) & (df['entrada'] != '') & (df['salida'] == '')
    df.loc[mascara, 'salida_activada'] = False
    guardar_excel(df)
    flash('🔒 Salida DESACTIVADA para TODOS los asistentes', 'warning')
    return redirect(url_for('admin'))

# Rutas para ENTRADA
@app.route('/admin/activar_entrada_todos/<int:conferencia_id>')
@requires_auth
def activar_entrada_todos(conferencia_id):
    """Activar entrada para TODOS los asistentes de una conferencia"""
    df = leer_excel()
    mascara = (df['conferencia_id'] == conferencia_id) & (df['entrada'] == '')
    df.loc[mascara, 'entrada_activada'] = True
    guardar_excel(df)
    flash('✅ ENTRADA ACTIVADA para TODOS los asistentes', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/desactivar_entrada_todos/<int:conferencia_id>')
@requires_auth
def desactivar_entrada_todos(conferencia_id):
    """Desactivar entrada para TODOS los asistentes de una conferencia"""
    df = leer_excel()
    mascara = (df['conferencia_id'] == conferencia_id) & (df['entrada'] == '')
    df.loc[mascara, 'entrada_activada'] = False
    guardar_excel(df)
    flash('🔒 ENTRADA DESACTIVADA para TODOS los asistentes', 'warning')
    return redirect(url_for('admin'))

@app.route('/ver_registros')
@requires_auth
def ver_registros():
    df = leer_excel()
    registros = df.to_dict('records')
    return render_template('ver_registros.html', registros=registros)

@app.route('/constancia', methods=['GET', 'POST'])
def constancia():
    if request.method == 'POST':
        email = request.form.get('email')
        conferencia_id = int(request.form.get('conferencia_id'))
        df = leer_excel()
        _, fila = obtener_fila_asistente(df, email, conferencia_id)
        if fila is None:
            flash('No se encontró ningún registro con ese email.', 'danger')
            return redirect(url_for('constancia'))
        if fila['entrada'] == '' or fila['salida'] == '':
            flash('❌ No puedes generar constancia porque faltan entrada o salida.', 'danger')
            return redirect(url_for('constancia'))
        pdf_file = generar_constancia_con_fondo(fila)
        nombre_limpio = fila['nombre'].replace(' ', '_').replace('/', '_')
        
        response = make_response(send_file(pdf_file, as_attachment=True,
                         download_name=f"constancia_{nombre_limpio}.pdf",
                         mimetype='application/pdf'))
        response.headers['Content-Disposition'] = f'attachment; filename="constancia_{nombre_limpio}.pdf"'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    return render_template('constancia.html', conferencias=CONFERENCIAS)

# Rutas para que el asistente descargue su constancia
@app.route('/constancia-qr', methods=['GET'])
def constancia_qr():
    return render_template('constancia_qr.html', conferencias=CONFERENCIAS)

@app.route('/descargar-constancia-qr', methods=['POST'])
def descargar_constancia_qr():
    email = request.form.get('email')
    conferencia_id = int(request.form.get('conferencia_id'))
    
    df = leer_excel()
    _, fila = obtener_fila_asistente(df, email, conferencia_id)
    
    if fila is None:
        flash('No se encontró ningún registro con ese correo para esa conferencia.', 'error')
        return redirect(url_for('constancia_qr'))
    
    if fila['entrada'] == '' or fila['salida'] == '':
        flash('❌ Aún no puedes generar la constancia. Debes tener entrada y salida registradas.', 'error')
        return redirect(url_for('constancia_qr'))
    
    try:
        pdf_file = generar_constancia_con_fondo(fila)
    except:
        pdf_file = generar_constancia_simple(fila)
    
    nombre_limpio = fila['nombre'].replace(' ', '_').replace('/', '_')
    return send_file(pdf_file, as_attachment=True,
                     download_name=f"constancia_{nombre_limpio}.pdf",
                     mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)