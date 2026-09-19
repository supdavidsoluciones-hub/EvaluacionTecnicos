import os
import uuid
from typing import List, Optional
from datetime import date, datetime
import openpyxl
from io import BytesIO
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import (
    InspectionCategory, InspectionChecklistTemplate, Inspection, InspectionItem,
    InspectionPhoto, NonConformity, Mobile, Technician, User
)
from backend.app.schemas.schemas import InspectionCreate, InspectionResponse
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/inspections", tags=["Inspecciones de Campo"])

# Directorio local de almacenamiento de imágenes (fallback local en servidor/Render)
UPLOADS_DIR = "static/uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

@router.get("/checklist-template")
def get_checklist_template(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    categories = db.query(InspectionCategory).order_by(InspectionCategory.sort_order.asc()).all()
    template_data = []
    for cat in categories:
        items = db.query(InspectionChecklistTemplate).filter(
            InspectionChecklistTemplate.category_id == cat.id,
            InspectionChecklistTemplate.is_active == True
        ).order_by(InspectionChecklistTemplate.sort_order.asc()).all()

        template_data.append({
            "category_id": cat.id,
            "category_name": cat.name,
            "category_code": cat.code,
            "questions": [{
                "id": q.id,
                "question_text": q.question_text
            } for q in items]
        })
    return template_data

@router.get("", response_model=List[dict])
def list_inspections(
    mobile_id: Optional[int] = None,
    technician_id: Optional[int] = None,
    inspection_date: Optional[date] = None,
    general_result: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Inspection)
    if mobile_id:
        query = query.filter(Inspection.mobile_id == mobile_id)
    if technician_id:
        query = query.filter(Inspection.technician_id == technician_id)
    if inspection_date:
        query = query.filter(Inspection.inspection_date == inspection_date)
    if general_result:
        query = query.filter(Inspection.general_result == general_result)

    inspections = query.order_by(Inspection.id.desc()).all()
    
    return [{
        "id": insp.id,
        "inspection_code": insp.inspection_code,
        "inspection_date": insp.inspection_date.isoformat(),
        "mobile_id": insp.mobile_id,
        "mobile_code": insp.mobile.code if insp.mobile else None,
        "technician_id": insp.technician_id,
        "technician_name": insp.technician.full_name if insp.technician else None,
        "order_number": insp.order_number,
        "order_type": insp.order_type,
        "general_result": insp.general_result,
        "photos_count": len(insp.photos),
        "non_conformities_count": len(insp.non_conformities),
        "supervisor_name": insp.supervisor.full_name if insp.supervisor else None
    } for insp in inspections]

@router.post("", response_model=dict)
def create_inspection(
    insp_in: InspectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_date = insp_in.inspection_date or date.today()
    
    # Generar código único de inspección: INS-YYYYMMDD-XXXX
    count_today = db.query(Inspection).filter(Inspection.inspection_date == target_date).count()
    code = f"INS-{target_date.strftime('%Y%m%d')}-{(count_today + 1):04d}"

    # Calcular resultado general en función de los ítems
    total_items = len(insp_in.items)
    no_cumple_count = sum(1 for it in insp_in.items if it.result == "No cumple")
    
    if no_cumple_count == 0:
        calculated_result = "Cumple"
    elif no_cumple_count <= 2:
        calculated_result = "Cumple parcialmente"
    else:
        calculated_result = "No cumple"

    # Si se envió un resultado explícito, respetarlo si no entra en conflicto severo
    final_general_result = insp_in.general_result or calculated_result

    inspection = Inspection(
        inspection_code=code,
        inspection_date=target_date,
        mobile_id=insp_in.mobile_id,
        technician_id=insp_in.technician_id,
        order_number=insp_in.order_number,
        order_type=insp_in.order_type,
        client_name=insp_in.client_name,
        contract_number=insp_in.contract_number,
        gps_lat=insp_in.gps_lat,
        gps_lon=insp_in.gps_lon,
        general_result=final_general_result,
        observations=insp_in.observations,
        corrective_action=insp_in.corrective_action,
        supervisor_id=current_user.id
    )
    db.add(inspection)
    db.flush()

    # Guardar ítems y crear No Conformidades automáticas para ítems con "No cumple"
    created_non_conformities = 0
    for item_in in insp_in.items:
        item_obj = InspectionItem(
            inspection_id=inspection.id,
            template_id=item_in.template_id,
            category_name=item_in.category_name,
            question_text=item_in.question_text,
            result=item_in.result,
            notes=item_in.notes
        )
        db.add(item_obj)

        if item_in.result == "No cumple":
            nc = NonConformity(
                inspection_id=inspection.id,
                mobile_id=insp_in.mobile_id,
                technician_id=insp_in.technician_id,
                category_name=item_in.category_name,
                description=f"Falla reportada en inspección {code}: {item_in.question_text}",
                corrective_action=insp_in.corrective_action or "Realizar corrección inmediata en sitio",
                responsible_person=current_user.full_name,
                status="Abierta"
            )
            db.add(nc)
            created_non_conformities += 1

    db.commit()
    db.refresh(inspection)
    
    return {
        "id": inspection.id,
        "inspection_code": inspection.inspection_code,
        "general_result": inspection.general_result,
        "non_conformities_created": created_non_conformities,
        "message": "Inspección creada exitosamente"
    }

@router.post("/{inspection_id}/photos")
async def upload_inspection_photo(
    inspection_id: int,
    file: UploadFile = File(...),
    photo_type: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspección no encontrada")

    # Subir fotografía usando servicio gratuito (Cloudinary o Local)
    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"

    contents = await file.read()
    from backend.app.services.storage import upload_image_to_free_cloud
    photo_url, key_id = upload_image_to_free_cloud(contents, unique_filename)

    photo_obj = InspectionPhoto(
        inspection_id=inspection_id,
        photo_url=photo_url,
        s3_key=key_id,
        photo_type=photo_type,
        caption=caption
    )
    db.add(photo_obj)
    db.commit()
    db.refresh(photo_obj)

    return {
        "id": photo_obj.id,
        "photo_url": photo_obj.photo_url,
        "message": "Fotografía guardada exitosamente"
    }

@router.get("/export")
async def export_inspections_excel(
    from_date: str = None,
    to_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export inspections to a modernized Excel file."""
    from datetime import date
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from io import BytesIO
    from fastapi.responses import StreamingResponse

    query = db.query(Inspection)

    if from_date:
        try:
            fd = date.fromisoformat(from_date)
            query = query.filter(Inspection.inspection_date >= fd)
        except ValueError:
            pass
    if to_date:
        try:
            td = date.fromisoformat(to_date)
            query = query.filter(Inspection.inspection_date <= td)
        except ValueError:
            pass

    inspections = query.order_by(Inspection.inspection_date.desc()).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte de Inspecciones"

    headers = [
        "CÓDIGO", "FECHA", "MÓVIL", "TÉCNICO", "TIPO ORDEN", "N° ORDEN",
        "CLIENTE", "RESULTADO GENERAL", "FALLAS REGISTRADAS (NO CUMPLE)", 
        "OBSERVACIONES", "FOTOS (EVIDENCIA)"
    ]
    ws.append(headers)

    # Styles
    header_fill = PatternFill("solid", fgColor="1A2B4A")
    header_font = Font(bold=True, color="FFFFFF", size=10)
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    border = Border(left=Side(style='thin', color='DDDDDD'), 
                    right=Side(style='thin', color='DDDDDD'), 
                    top=Side(style='thin', color='DDDDDD'), 
                    bottom=Side(style='thin', color='DDDDDD'))
    
    pass_fill = PatternFill("solid", fgColor="E6F9F0")
    pass_font = Font(color="1E7C50", bold=True)
    fail_fill = PatternFill("solid", fgColor="FEE8E8")
    fail_font = Font(color="C0392B", bold=True)
    warn_fill = PatternFill("solid", fgColor="FFF8E1")
    warn_font = Font(color="B7860D", bold=True)

    # Apply header styles
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = align_center

    row_num = 2
    for ins in inspections:
        mobile_code = ins.mobile.code if ins.mobile else "N/A"
        tech_name = ins.technician.full_name if ins.technician else "N/A"
        
        # Get failures
        failures = [f"- {it.question_text}" for it in ins.items if it.result == "No cumple"]
        failures_str = "\n".join(failures) if failures else "Sin fallas"

        # Get photos
        photos = [p.photo_url for p in ins.photos if p.photo_url]
        photos_str = "\n\n".join(photos) if photos else "Sin evidencias"

        row_data = [
            ins.inspection_code or "",
            str(ins.inspection_date) if ins.inspection_date else "",
            mobile_code,
            tech_name,
            ins.order_type or "",
            ins.order_number or "",
            ins.client_name or "",
            ins.general_result or "",
            failures_str,
            ins.observations or "Ninguna",
            photos_str
        ]
        ws.append(row_data)

        # Apply styles to row
        for col_idx, cell in enumerate(ws[row_num], 1):
            cell.border = border
            if col_idx == 8: # Resultado General
                cell.alignment = align_center
                if cell.value == 'Cumple':
                    cell.fill, cell.font = pass_fill, pass_font
                elif cell.value == 'No cumple':
                    cell.fill, cell.font = fail_fill, fail_font
                else:
                    cell.fill, cell.font = warn_fill, warn_font
            elif col_idx in (9, 10, 11): # Text fields
                cell.alignment = align_left
            else:
                cell.alignment = align_center
        
        # Make links clickable for photos
        if photos_str != "Sin evidencias":
            # Just set hyperlinking styling
            ws.cell(row=row_num, column=11).font = Font(color="0563C1", underline="single")
            
        row_num += 1

    # Column widths
    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['D'].width = 25
    ws.column_dimensions['E'].width = 25
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 20
    ws.column_dimensions['H'].width = 20
    ws.column_dimensions['I'].width = 40
    ws.column_dimensions['J'].width = 30
    ws.column_dimensions['K'].width = 50

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"Inspecciones_{from_date or 'inicio'}_al_{to_date or 'hoy'}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/{inspection_id}")
def get_inspection_detail(inspection_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Inspección no encontrada")

    return {
        "id": insp.id,
        "inspection_code": insp.inspection_code,
        "inspection_date": insp.inspection_date.isoformat(),
        "mobile_id": insp.mobile_id,
        "mobile_code": insp.mobile.code if insp.mobile else None,
        "technician_id": insp.technician_id,
        "technician_name": insp.technician.full_name if insp.technician else None,
        "order_number": insp.order_number,
        "order_type": insp.order_type,
        "general_result": insp.general_result,
        "observations": insp.observations,
        "corrective_action": insp.corrective_action,
        "supervisor_name": insp.supervisor.full_name if insp.supervisor else None,
        "items": [{
            "id": it.id,
            "category_name": it.category_name,
            "question_text": it.question_text,
            "result": it.result,
            "notes": it.notes
        } for it in insp.items],
        "photos": [{
            "id": p.id,
            "photo_url": p.photo_url,
            "photo_type": p.photo_type,
            "caption": p.caption,
            "created_at": p.created_at.isoformat()
        } for p in insp.photos],
        "non_conformities": [{
            "id": nc.id,
            "category_name": nc.category_name,
            "description": nc.description,
            "status": nc.status
        } for nc in insp.non_conformities]
    }

