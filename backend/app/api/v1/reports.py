import io
import pandas as pd
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Order, Inspection, Guarantee, Mobile, User
from backend.app.api.deps import get_current_user
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

router = APIRouter(prefix="/reports", tags=["Reportes y Exportaciones"])

@router.get("/export/excel")
def export_excel_report(
    report_type: str = Query("orders", description="Tipo: orders, inspections, guarantees, production"),
    target_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    output = io.BytesIO()
    
    if report_type == "orders":
        orders = db.query(Order).order_by(Order.order_date.desc()).all()
        data = [{
            "Orden #": o.order_number,
            "Fecha": o.order_date.isoformat(),
            "Móvil": o.mobile.code if o.mobile else "",
            "Técnico Principal": o.primary_technician.full_name if o.primary_technician else "",
            "Técnico Auxiliar": o.secondary_technician.full_name if o.secondary_technician else "",
            "Tipo": o.order_type,
            "Hora Inicio": o.start_time or "",
            "Hora Fin": o.end_time or "",
            "Duración (Min)": o.duration_minutes,
            "Superó 45 Min": "SÍ" if o.exceeds_target_time else "NO",
            "Estado": o.status,
            "Observaciones": o.notes or ""
        } for o in orders]
        df = pd.DataFrame(data)
        sheet_name = "Órdenes"
    
    elif report_type == "guarantees":
        guarantees = db.query(Guarantee).order_by(Guarantee.guarantee_date.desc()).all()
        data = [{
            "Garantía #": g.guarantee_number,
            "Orden Original #": g.original_order_number,
            "Fecha": g.guarantee_date.isoformat(),
            "Móvil": g.mobile.code if g.mobile else "",
            "Técnico": g.technician.full_name if g.technician else "",
            "Tipo Garantía": g.guarantee_type,
            "Causa": g.cause,
            "Reincidencia": "SÍ" if g.is_reincidence else "NO",
            "Notas": g.notes or ""
        } for g in guarantees]
        df = pd.DataFrame(data)
        sheet_name = "Garantías"

    else:
        # Default report: Inspections
        inspections = db.query(Inspection).order_by(Inspection.inspection_date.desc()).all()
        data = [{
            "Código Inspección": i.inspection_code,
            "Fecha": i.inspection_date.isoformat(),
            "Móvil": i.mobile.code if i.mobile else "",
            "Técnico": i.technician.full_name if i.technician else "",
            "Orden #": i.order_number,
            "Tipo": i.order_type,
            "Resultado General": i.general_result,
            "Supervisor": i.supervisor.full_name if i.supervisor else "",
            "Observaciones": i.observations or ""
        } for i in inspections]
        df = pd.DataFrame(data)
        sheet_name = "Inspecciones"

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)

    output.seek(0)
    filename = f"reporte_{report_type}_{date.today().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/export/pdf")
def export_pdf_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=12
    )

    story.append(Paragraph("REPORTE OPERATIVO DE MÓVILES - CHIRIQUÍ", title_style))
    story.append(Paragraph(f"Fecha de emisión: {date.today().strftime('%d/%m/%Y')}", styles['Normal']))
    story.append(Spacer(1, 15))

    # Tabla resumen por móvil
    mobiles = db.query(Mobile).order_by(Mobile.code.asc()).all()
    table_data = [["Móvil", "Órdenes", "Completadas", "Garantías", "Índice %", "Estado"]]

    for m in mobiles:
        completed = db.query(Order).filter(Order.mobile_id == m.id, Order.status == "Completada").count()
        total_o = db.query(Order).filter(Order.mobile_id == m.id).count()
        guarantees = db.query(Guarantee).filter(Guarantee.mobile_id == m.id).count()
        g_idx = round((guarantees / completed * 100), 1) if completed > 0 else 0.0
        
        status_txt = "OK" if g_idx <= 5.0 else "ALERTA"
        table_data.append([m.code, str(total_o), str(completed), str(guarantees), f"{g_idx}%", status_txt])

    t = Table(table_data, colWidths=[80, 80, 90, 80, 80, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
    ]))

    story.append(t)
    doc.build(story)
    
    buffer.seek(0)
    filename = f"reporte_operativo_chiriqui_{date.today().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
