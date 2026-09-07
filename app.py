import os
import uuid
import io
from datetime import datetime

import psycopg2
import psycopg2.extras
import cloudinary
import cloudinary.uploader
from flask import (
    Flask, render_template, request, redirect,
    url_for, jsonify, send_file, abort
)
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

# ─── Cloudinary ────────────────────────────────────────────────────────────────
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', 'dgb8eri7'),
    api_key=os.environ.get('CLOUDINARY_API_KEY', ''),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET', ''),
    secure=True,
)
CLOUDINARY_UPLOAD_PRESET = os.environ.get('CLOUDINARY_UPLOAD_PRESET', 'chiriqui_fotos')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'heic', 'heif'}

# ─── Base de Datos (PostgreSQL) ────────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres:bZIqGZes2ZuNMXZ6@db.vpivzxkttjsgkpxyvpvp.supabase.co:5432/postgres'
)
# Render usa postgres:// pero psycopg2 necesita postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)


def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS moviles (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL UNIQUE,
            tecnico1 TEXT NOT NULL,
            tecnico2 TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS inspecciones (
            id SERIAL PRIMARY KEY,
            uuid TEXT NOT NULL UNIQUE,
            fecha TEXT NOT NULL,
            movil TEXT NOT NULL,
            nombre_cliente TEXT NOT NULL,
            numero_contrato TEXT NOT NULL,
            tipo_orden TEXT NOT NULL,
            tecnico1 TEXT NOT NULL,
            tecnico2 TEXT,
            cr_normas_instalacion INTEGER,
            cr_rutas_instalacion INTEGER,
            cr_config_equipos INTEGER,
            cr_explicacion_wifi INTEGER,
            cr_explico_caja_tv INTEGER,
            cr_conecto_wifi INTEGER,
            cr_explico_bondades INTEGER,
            cr_eero TEXT,
            cr_cableado_fibra INTEGER,
            cr_recorrido_nap INTEGER,
            cr_seguridad_epp INTEGER,
            cr_limpieza INTEGER,
            fotos_inspeccion TEXT,
            tiempo_traslado INTEGER,
            tiempo_iniciacion INTEGER,
            tiempo_cierre INTEGER,
            coordinan_tiempos TEXT,
            observaciones_tiempos TEXT,
            vehiculo_limpieza TEXT,
            vehiculo_carroceria TEXT,
            vehiculo_accidente TEXT,
            vehiculo_detalle_accidente TEXT,
            fotos_vehiculo TEXT,
            notas_finales TEXT,
            total_obtenido INTEGER,
            max_posible INTEGER,
            porcentaje REAL,
            nivel TEXT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()


# Inicializar BD al arrancar
try:
    init_db()
except Exception as e:
    print(f"[WARN] DB init: {e}")

# ─── Helpers ───────────────────────────────────────────────────────────────────
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_files_to_cloudinary(files, folder='inspecciones'):
    """Sube archivos a Cloudinary y devuelve lista de URLs seguras."""
    urls = []
    for f in files:
        if f and f.filename and allowed_file(f.filename):
            try:
                result = cloudinary.uploader.upload(
                    f,
                    folder=f'calidad_tec/{folder}',
                    resource_type='image',
                    upload_preset=CLOUDINARY_UPLOAD_PRESET if CLOUDINARY_UPLOAD_PRESET else None,
                )
                urls.append(result.get('secure_url', ''))
            except Exception as e:
                print(f"[Cloudinary ERROR] {e}")
    return [u for u in urls if u]


def calcular_puntuacion(form):
    numericos = {
        'cr_normas_instalacion': int(form.get('cr_normas_instalacion', 5)),
        'cr_rutas_instalacion': int(form.get('cr_rutas_instalacion', 5)),
        'cr_config_equipos': int(form.get('cr_config_equipos', 5)),
        'cr_explicacion_wifi': int(form.get('cr_explicacion_wifi', 5)),
        'cr_explico_caja_tv': int(form.get('cr_explico_caja_tv', 5)),
        'cr_conecto_wifi': int(form.get('cr_conecto_wifi', 5)),
        'cr_explico_bondades': int(form.get('cr_explico_bondades', 5)),
        'cr_cableado_fibra': int(form.get('cr_cableado_fibra', 5)),
        'cr_recorrido_nap': int(form.get('cr_recorrido_nap', 5)),
        'cr_seguridad_epp': int(form.get('cr_seguridad_epp', 5)),
        'cr_limpieza': int(form.get('cr_limpieza', 5)),
    }
    total = sum(numericos.values())
    max_p = len(numericos) * 5

    eero = form.get('cr_eero', 'no_aplica')
    if eero == 'si':
        total += 5
        max_p += 5
    elif eero == 'no':
        total += 1
        max_p += 5

    porcentaje = round((total / max_p) * 100, 1) if max_p else 0

    if porcentaje >= 90:
        nivel = 'Excelente'
    elif porcentaje >= 80:
        nivel = 'Bueno'
    elif porcentaje >= 70:
        nivel = 'Regular'
    else:
        nivel = 'Deficiente'

    return numericos, eero, total, max_p, porcentaje, nivel

# ─── Rutas ─────────────────────────────────────────────────────────────────────

@app.route('/')
def inicio():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM moviles ORDER BY nombre')
    moviles = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('evaluacion.html', moviles=moviles)


@app.route('/api/moviles')
def api_moviles():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT nombre, tecnico1, tecnico2 FROM moviles')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    data = {r['nombre']: {'tecnico1': r['tecnico1'], 'tecnico2': r['tecnico2'] or ''} for r in rows}
    return jsonify(data)


@app.route('/evaluar', methods=['POST'])
def evaluar():
    movil = request.form.get('movil', '').strip()
    nombre_cliente = request.form.get('nombre_cliente', '').strip()
    contrato_raw = request.form.get('contrato', '').strip()
    contrato = f"P-{contrato_raw}" if not contrato_raw.startswith('P-') else contrato_raw
    tipo_orden = request.form.get('tipo_orden', '').strip()
    tecnico1 = request.form.get('tecnico1', '').strip()
    tecnico2 = request.form.get('tecnico2', '').strip() or 'N/A'

    numericos, eero, total, max_p, porcentaje, nivel = calcular_puntuacion(request.form)

    tiempo_traslado = int(request.form.get('tiempo_traslado', 0) or 0)
    tiempo_iniciacion = int(request.form.get('tiempo_iniciacion', 0) or 0)
    tiempo_cierre = int(request.form.get('tiempo_cierre', 0) or 0)
    coordinan = request.form.get('coordinan_tiempos', 'Sí')
    obs_tiempos = request.form.get('observaciones_tiempos', '').strip()

    vehiculo_limpieza = request.form.get('vehiculo_limpieza', '').strip()
    vehiculo_carroceria = request.form.get('vehiculo_carroceria', '').strip()
    vehiculo_accidente = request.form.get('vehiculo_accidente', 'No')
    vehiculo_detalle = request.form.get('vehiculo_detalle_accidente', '').strip()
    notas_finales = request.form.get('notas_finales', '').strip()

    inspeccion_uid = uuid.uuid4().hex
    fecha = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Subir fotos a Cloudinary
    fotos_insp = upload_files_to_cloudinary(
        request.files.getlist('fotos_inspeccion'),
        folder=f'inspecciones/{inspeccion_uid}'
    )
    fotos_veh = upload_files_to_cloudinary(
        request.files.getlist('fotos_vehiculo'),
        folder=f'vehiculos/{inspeccion_uid}'
    )

    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO inspecciones (
            uuid, fecha, movil, nombre_cliente, numero_contrato, tipo_orden,
            tecnico1, tecnico2,
            cr_normas_instalacion, cr_rutas_instalacion, cr_config_equipos,
            cr_explicacion_wifi, cr_explico_caja_tv, cr_conecto_wifi,
            cr_explico_bondades, cr_eero, cr_cableado_fibra, cr_recorrido_nap,
            cr_seguridad_epp, cr_limpieza,
            fotos_inspeccion, tiempo_traslado, tiempo_iniciacion, tiempo_cierre,
            coordinan_tiempos, observaciones_tiempos,
            vehiculo_limpieza, vehiculo_carroceria, vehiculo_accidente,
            vehiculo_detalle_accidente, fotos_vehiculo, notas_finales,
            total_obtenido, max_posible, porcentaje, nivel
        ) VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        ) RETURNING id
    ''', (
        inspeccion_uid, fecha, movil, nombre_cliente, contrato, tipo_orden,
        tecnico1, tecnico2,
        numericos['cr_normas_instalacion'], numericos['cr_rutas_instalacion'],
        numericos['cr_config_equipos'], numericos['cr_explicacion_wifi'],
        numericos['cr_explico_caja_tv'], numericos['cr_conecto_wifi'],
        numericos['cr_explico_bondades'], eero,
        numericos['cr_cableado_fibra'], numericos['cr_recorrido_nap'],
        numericos['cr_seguridad_epp'], numericos['cr_limpieza'],
        '|'.join(fotos_insp), tiempo_traslado, tiempo_iniciacion, tiempo_cierre,
        coordinan, obs_tiempos,
        vehiculo_limpieza, vehiculo_carroceria, vehiculo_accidente,
        vehiculo_detalle, '|'.join(fotos_veh), notas_finales,
        total, max_p, porcentaje, nivel
    ))
    insp_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('resultado', insp_id=insp_id))


@app.route('/resultado/<int:insp_id>')
def resultado(insp_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM inspecciones WHERE id=%s', (insp_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        abort(404)

    fotos_insp = [f for f in (row['fotos_inspeccion'] or '').split('|') if f]
    fotos_veh = [f for f in (row['fotos_vehiculo'] or '').split('|') if f]
    clase = {'Excelente': 'excelente', 'Bueno': 'bueno', 'Regular': 'regular', 'Deficiente': 'deficiente'}.get(row['nivel'], 'regular')

    tiempos = {
        'traslado': row['tiempo_traslado'] or 0,
        'iniciacion': row['tiempo_iniciacion'] or 0,
        'cierre': row['tiempo_cierre'] or 0,
        'demora': (row['tiempo_traslado'] or 0) + (row['tiempo_iniciacion'] or 0),
        'total': (row['tiempo_traslado'] or 0) + (row['tiempo_iniciacion'] or 0) + (row['tiempo_cierre'] or 0),
        'coordinan': row['coordinan_tiempos'],
        'obs': row['observaciones_tiempos'],
    }

    CRITERIOS_LABELS = {
        'cr_normas_instalacion': 'Cumplió con las normas de instalación',
        'cr_rutas_instalacion': 'Utilizó rutas adecuadas de instalación',
        'cr_config_equipos': 'Configuración correcta en módem, cajas TV y extensores',
        'cr_explicacion_wifi': 'Explicó el WiFi al cliente',
        'cr_explico_caja_tv': 'Explicó el uso de la caja de TV',
        'cr_conecto_wifi': 'Conectó al cliente a la red WiFi',
        'cr_explico_bondades': 'Explicó las bondades del servicio',
        'cr_cableado_fibra': 'Cableado de fibra óptica correcto',
        'cr_recorrido_nap': 'Recorrido correcto en la caja NAP',
        'cr_seguridad_epp': 'Uso de EPP (conos, casco, arnés)',
        'cr_limpieza': 'Limpieza y orden en el área de trabajo',
    }
    criterios = {label: row[key] for key, label in CRITERIOS_LABELS.items()}

    return render_template('resultado.html', row=row, criterios=criterios,
                           eero=row['cr_eero'], fotos_insp=fotos_insp,
                           fotos_veh=fotos_veh, clase=clase, tiempos=tiempos)


@app.route('/historial')
def historial():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        SELECT id, fecha, movil, nombre_cliente, numero_contrato,
               tipo_orden, tecnico1, porcentaje, nivel
        FROM inspecciones ORDER BY id DESC
    ''')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('historial.html', inspecciones=rows)


@app.route('/exportar_excel')
def exportar_excel():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM inspecciones ORDER BY id DESC')
    rows = cur.fetchall()
    cur.close()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Inspecciones'

    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='3730A3', end_color='3730A3', fill_type='solid')
    alt_fill = PatternFill(start_color='EEF2FF', end_color='EEF2FF', fill_type='solid')
    center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left = Alignment(horizontal='left', vertical='center', wrap_text=True)
    thin = Side(style='thin', color='CBD5E1')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    score_fills = {
        'Excelente': PatternFill(start_color='D1FAE5', end_color='D1FAE5', fill_type='solid'),
        'Bueno':     PatternFill(start_color='DBEAFE', end_color='DBEAFE', fill_type='solid'),
        'Regular':   PatternFill(start_color='FEF3C7', end_color='FEF3C7', fill_type='solid'),
        'Deficiente':PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid'),
    }

    headers = [
        'ID', 'Fecha', 'Móvil', 'Cliente', 'Contrato', 'Tipo de Orden',
        'Técnico 1', 'Técnico 2',
        'Normas Instalación', 'Rutas Instalación', 'Config. Equipos',
        'Explicó WiFi', 'Explicó Caja TV', 'Conectó WiFi', 'Explicó Bondades',
        'Eero', 'Cableado Fibra', 'Recorrido NAP', 'EPP Seguridad', 'Limpieza',
        'Traslado (min)', 'Iniciación (min)', 'Cierre (min)', '¿Coordinan Tiempos?',
        'Obs. Tiempos', 'Limpieza Vehículo', 'Carrocería', 'Accidente',
        'Detalle Accidente', 'Total Obtenido', 'Máximo Posible',
        'Porcentaje (%)', 'Nivel', 'Notas Finales',
    ]

    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = border
    ws.row_dimensions[1].height = 35

    eero_labels = {
        'si': '✔ Sí, configuró Eero',
        'no': '✘ No configuró Eero',
        'no_aplica': '— No aplica'
    }

    for row_idx, r in enumerate(rows, 2):
        data = [
            r['id'], r['fecha'], r['movil'], r['nombre_cliente'],
            r['numero_contrato'], r['tipo_orden'], r['tecnico1'], r['tecnico2'] or 'N/A',
            r['cr_normas_instalacion'], r['cr_rutas_instalacion'], r['cr_config_equipos'],
            r['cr_explicacion_wifi'], r['cr_explico_caja_tv'], r['cr_conecto_wifi'],
            r['cr_explico_bondades'],
            eero_labels.get(r['cr_eero'], r['cr_eero']),
            r['cr_cableado_fibra'], r['cr_recorrido_nap'],
            r['cr_seguridad_epp'], r['cr_limpieza'],
            r['tiempo_traslado'], r['tiempo_iniciacion'], r['tiempo_cierre'],
            r['coordinan_tiempos'], r['observaciones_tiempos'],
            r['vehiculo_limpieza'], r['vehiculo_carroceria'], r['vehiculo_accidente'],
            r['vehiculo_detalle_accidente'],
            r['total_obtenido'], r['max_posible'], r['porcentaje'], r['nivel'],
            r['notas_finales'],
        ]
        ws.append(data)
        nivel_fill = score_fills.get(r['nivel'], PatternFill(fill_type=None))
        nivel_col = headers.index('Nivel') + 1

        for col_idx in range(1, len(data) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = border
            cell.alignment = left
            if col_idx == nivel_col:
                cell.fill = nivel_fill
                cell.font = Font(bold=True)
            elif row_idx % 2 == 0:
                cell.fill = alt_fill

        ws.row_dimensions[row_idx].height = 20

    col_widths = [6, 18, 14, 22, 15, 14, 24, 24, 10, 10, 12, 10, 10,
                  10, 10, 24, 10, 10, 10, 10, 10, 10, 10, 18, 28, 16,
                  16, 12, 28, 10, 10, 12, 12, 42]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = 'A2'

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"inspecciones_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ─── Configuración de Móviles ──────────────────────────────────────────────────

@app.route('/configuracion')
def configuracion():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM moviles ORDER BY nombre')
    moviles = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('configuracion.html', moviles=moviles)


@app.route('/configuracion/guardar', methods=['POST'])
def guardar_movil():
    nombre = request.form.get('nombre', '').strip()
    tecnico1 = request.form.get('tecnico1', '').strip()
    tecnico2 = request.form.get('tecnico2', '').strip()
    movil_id = request.form.get('id', '').strip()

    conn = get_db()
    cur = conn.cursor()
    if movil_id:
        cur.execute('UPDATE moviles SET nombre=%s, tecnico1=%s, tecnico2=%s WHERE id=%s',
                    (nombre, tecnico1, tecnico2, movil_id))
    else:
        cur.execute('''
            INSERT INTO moviles (nombre, tecnico1, tecnico2)
            VALUES (%s, %s, %s)
            ON CONFLICT (nombre) DO UPDATE SET tecnico1=EXCLUDED.tecnico1, tecnico2=EXCLUDED.tecnico2
        ''', (nombre, tecnico1, tecnico2))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('configuracion'))


@app.route('/configuracion/eliminar/<int:movil_id>', methods=['POST'])
def eliminar_movil(movil_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM moviles WHERE id=%s', (movil_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('configuracion'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
