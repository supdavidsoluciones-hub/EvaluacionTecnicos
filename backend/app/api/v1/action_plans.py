import os
import uuid
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import ActionPlan, ActionPlanEvidence, Mobile, User
from backend.app.schemas.schemas import ActionPlanCreate, ActionPlanResponse
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/action-plans", tags=["Plan de Acción"])

UPLOADS_DIR = "static/uploads"

@router.get("", response_model=List[dict])
def list_action_plans(
    mobile_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(ActionPlan)
    if mobile_id:
        query = query.filter(ActionPlan.mobile_id == mobile_id)
    if status:
        query = query.filter(ActionPlan.status == status)

    plans = query.order_by(ActionPlan.due_date.asc()).all()
    today = date.today()

    result = []
    for p in plans:
        # Evaluar si está vencido automáticamente
        current_status = p.status
        if current_status not in ["Completado"] and p.due_date < today:
            current_status = "Vencido"

        result.append({
            "id": p.id,
            "mobile_id": p.mobile_id,
            "mobile_code": p.mobile.code if p.mobile else None,
            "detected_problem": p.detected_problem,
            "corrective_action": p.corrective_action,
            "responsible_person": p.responsible_person,
            "start_date": p.start_date.isoformat(),
            "due_date": p.due_date.isoformat(),
            "status": current_status,
            "notes": p.notes,
            "evidences": [{
                "id": ev.id,
                "photo_url": ev.photo_url,
                "notes": ev.notes,
                "uploaded_at": ev.uploaded_at.isoformat()
            } for ev in p.evidences]
        })
    return result

@router.post("", response_model=ActionPlanResponse)
def create_action_plan(
    plan_in: ActionPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    start = plan_in.start_date or date.today()
    plan = ActionPlan(
        mobile_id=plan_in.mobile_id,
        detected_problem=plan_in.detected_problem,
        corrective_action=plan_in.corrective_action,
        responsible_person=plan_in.responsible_person,
        start_date=start,
        due_date=plan_in.due_date,
        status=plan_in.status or "Pendiente",
        notes=plan_in.notes
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

@router.put("/{plan_id}/status")
def update_action_plan_status(
    plan_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    plan = db.query(ActionPlan).filter(ActionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan de acción no encontrado")
    
    valid_statuses = ["Pendiente", "En proceso", "Completado", "Vencido"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Opciones: {valid_statuses}")

    plan.status = status
    db.commit()
    return {"message": f"Plan de acción {plan_id} actualizado a estado '{status}'"}

@router.post("/{plan_id}/evidence")
async def upload_plan_evidence(
    plan_id: int,
    file: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    plan = db.query(ActionPlan).filter(ActionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan de acción no encontrado")

    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    unique_filename = f"plan_{uuid.uuid4().hex}{file_ext}"
    saved_path = os.path.join(UPLOADS_DIR, unique_filename)

    contents = await file.read()
    with open(saved_path, "wb") as f:
        f.write(contents)

    photo_url = f"/static/uploads/{unique_filename}"

    ev = ActionPlanEvidence(
        action_plan_id=plan_id,
        photo_url=photo_url,
        notes=notes
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    return {
        "id": ev.id,
        "photo_url": ev.photo_url,
        "message": "Evidencia cargada exitosamente"
    }
