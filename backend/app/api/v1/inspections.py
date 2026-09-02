import os
import uuid
from typing import List, Optional
from datetime import date, datetime
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
