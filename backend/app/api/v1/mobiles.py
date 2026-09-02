from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Mobile, Technician, MobileTechnicianHistory, User
from backend.app.schemas.schemas import MobileCreate, MobileResponse, AssignTechniciansRequest
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/mobiles", tags=["Móviles"])

@router.get("", response_model=List[dict])
def list_mobiles(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mobiles = db.query(Mobile).order_by(Mobile.code.asc()).all()
    result = []
    for m in mobiles:
        history_active = db.query(MobileTechnicianHistory).filter(
            MobileTechnicianHistory.mobile_id == m.id,
            MobileTechnicianHistory.end_date == None
        ).all()
        
        primary_tech = None
        secondary_tech = None
        for h in history_active:
            if h.role_in_mobile == "principal":
                primary_tech = {"id": h.technician.id, "name": h.technician.full_name}
            elif h.role_in_mobile == "auxiliar":
                secondary_tech = {"id": h.technician.id, "name": h.technician.full_name}

        result.append({
            "id": m.id,
            "code": m.code,
            "status": m.status,
            "notes": m.notes,
            "created_at": m.created_at.isoformat(),
            "primary_technician": primary_tech,
            "secondary_technician": secondary_tech
        })
    return result

@router.post("", response_model=MobileResponse)
def create_mobile(mobile_in: MobileCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(Mobile).filter(Mobile.code == mobile_in.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"La móvil {mobile_in.code} ya existe")
    mobile = Mobile(code=mobile_in.code, status=mobile_in.status, notes=mobile_in.notes)
    db.add(mobile)
    db.commit()
    db.refresh(mobile)
    return mobile

@router.post("/{mobile_id}/assign-technicians")
def assign_technicians(
    mobile_id: int,
    assign_data: AssignTechniciansRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    mobile = db.query(Mobile).filter(Mobile.id == mobile_id).first()
    if not mobile:
        raise HTTPException(status_code=404, detail="Móvil no encontrada")

    # Cerrar asignaciones activas previas de esta móvil
    now = datetime.utcnow()
    active_histories = db.query(MobileTechnicianHistory).filter(
        MobileTechnicianHistory.mobile_id == mobile_id,
        MobileTechnicianHistory.end_date == None
    ).all()
    for h in active_histories:
        h.end_date = now

    # Asignar técnico principal
    tech1 = db.query(Technician).filter(Technician.id == assign_data.primary_technician_id).first()
    if not tech1:
        raise HTTPException(status_code=404, detail="Técnico principal no encontrado")
    
    tech1.current_mobile_id = mobile_id
    h1 = MobileTechnicianHistory(
        mobile_id=mobile_id,
        technician_id=tech1.id,
        role_in_mobile="principal",
        start_date=now,
        assigned_by_user_id=current_user.id,
        notes=assign_data.notes
    )
    db.add(h1)

    # Asignar técnico secundario si fue indicado
    if assign_data.secondary_technician_id:
        tech2 = db.query(Technician).filter(Technician.id == assign_data.secondary_technician_id).first()
        if tech2:
            tech2.current_mobile_id = mobile_id
            h2 = MobileTechnicianHistory(
                mobile_id=mobile_id,
                technician_id=tech2.id,
                role_in_mobile="auxiliar",
                start_date=now,
                assigned_by_user_id=current_user.id,
                notes=assign_data.notes
            )
            db.add(h2)

    db.commit()
    return {"message": f"Técnicos asignados correctamente a móvil {mobile.code}"}

@router.get("/{mobile_id}/history")
def get_mobile_history(mobile_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    history = db.query(MobileTechnicianHistory).filter(
        MobileTechnicianHistory.mobile_id == mobile_id
    ).order_by(MobileTechnicianHistory.start_date.desc()).all()
    
    return [{
        "id": h.id,
        "technician_id": h.technician.id,
        "technician_name": h.technician.full_name,
        "role_in_mobile": h.role_in_mobile,
        "start_date": h.start_date.isoformat(),
        "end_date": h.end_date.isoformat() if h.end_date else None,
        "notes": h.notes
    } for h in history]
