from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route("/")
def inicio():
    return render_template("evaluacion.html")

@app.route("/evaluar", methods=["POST"])
@app.route("/resultado", methods=["POST"])
def evaluar():
    # Información general
    movil = request.form.get("movil", "").strip()
    contrato_raw = request.form.get("contrato", "").strip()
    contrato = f"P-{contrato_raw}" if not contrato_raw.startswith("P-") else contrato_raw
    tecnico1 = request.form.get("tecnico1", "").strip()
    tecnico2 = request.form.get("tecnico2", "").strip() or "N/A"

    # Evaluaciones numéricas (1 a 5)
    criterios_numericos = {
        "1. Colocación correcta de la acometida": int(request.form.get("criterio_acometida", 5)),
        "2. Uso de equipo de seguridad (EPP)": int(request.form.get("criterio_epp", 5)),
        "3. Recorrido correcto del NAP": int(request.form.get("criterio_nap", 5)),
        "4. Ingreso correcto a la residencia (acometida)": int(request.form.get("criterio_ingreso_residencia", 5)),
        "5. Estética dentro de la casa del cableado": int(request.form.get("criterio_estetica_cableado", 5)),
        "6. Buena colocación del módem": int(request.form.get("criterio_colocacion_modem", 5)),
        "7. Funcionamiento correcto del equipo y cajas TV": int(request.form.get("criterio_funcionamiento_equipos", 5)),
        "8. Explicación correcta al cliente sobre el uso de la caja TV": int(request.form.get("criterio_explicacion_caja_tv", 5)),
        "10. Buen cierre de orden con el uso correcto de las fotos": int(request.form.get("criterio_cierre_fotos", 5)),
        "11. Prueba de velocidad mostrada al cliente": int(request.form.get("criterio_prueba_velocidad", 5)),
    }

    video_tv = request.form.get("criterio_video_caja_tv", "No amerita")

    # Puntuación
    total_obtenido = sum(criterios_numericos.values())
    max_posible = len(criterios_numericos) * 5

    if video_tv == "Sí":
        total_obtenido += 5
        max_posible += 5
    elif video_tv == "No":
        total_obtenido += 1
        max_posible += 5
    # Si es "No amerita", no altera el total del max_posible

    porcentaje = round((total_obtenido / max_posible) * 100, 1)

    # Clasificación por nivel
    if porcentaje >= 90:
        nivel = "Excelente"
        clase_nivel = "excelente"
    elif porcentaje >= 80:
        nivel = "Bueno"
        clase_nivel = "bueno"
    elif porcentaje >= 70:
        nivel = "Regular"
        clase_nivel = "regular"
    else:
        nivel = "Deficiente"
        clase_nivel = "deficiente"

    # Control de Tiempos y Demoras
    tiempo_traslado = int(request.form.get("tiempo_traslado", 0))
    tiempo_iniciacion = int(request.form.get("tiempo_iniciacion", 0))
    tiempo_cierre = int(request.form.get("tiempo_cierre", 0))
    coordinan_tiempos = request.form.get("coordinan_tiempos", "Sí")
    observaciones_tiempos = request.form.get("observaciones_tiempos", "").strip()

    demora_traslado_iniciacion = tiempo_traslado + tiempo_iniciacion
    tiempo_total_orden = demora_traslado_iniciacion + tiempo_cierre

    tiempos = {
        "tiempo_traslado": tiempo_traslado,
        "tiempo_iniciacion": tiempo_iniciacion,
        "tiempo_cierre": tiempo_cierre,
        "demora_traslado_iniciacion": demora_traslado_iniciacion,
        "tiempo_total_orden": tiempo_total_orden,
        "coordinan_tiempos": coordinan_tiempos,
        "observaciones": observaciones_tiempos
    }

    return render_template(
        "resultado.html",
        movil=movil,
        contrato=contrato,
        tecnico1=tecnico1,
        tecnico2=tecnico2,
        criterios=criterios_numericos,
        video_tv=video_tv,
        total_obtenido=total_obtenido,
        max_posible=max_posible,
        porcentaje=porcentaje,
        nivel=nivel,
        clase_nivel=clase_nivel,
        tiempos=tiempos
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)
