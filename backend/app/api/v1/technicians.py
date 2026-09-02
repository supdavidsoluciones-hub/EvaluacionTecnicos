from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Technician, MobileTechnicianHistory, User
from backend.app.schemas.schemas import TechnicianCreate, TechnicianResponse
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/technicians", tags=["Técnicos"])

@router.get("", response_model=List[dict])
def list_technicians(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    techs = db.query(Technician).order_by(Technician.full_name.asc()).all()
    result = []
    for t in techs:
        mobile_code = t.current_mobile.code if t.current_mobile else None
        result.append({
            "id": t.id,
            "full_name": t.full_name,
            "status": t.status,
            "current_mobile_id": t.current_mobile_id,
            "current_mobile_code": mobile_code,
            "hire_date": t.hire_date.isoformat() if t.hire_date else None,
            "notes": t.notes
        })
    return result

@router.post("", response_model=TechnicianResponse)
def create_technician(tech_in: TechnicianCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tech = Technician(
        full_name=tech_in.full_name,
        status=tech_in.status,
        current_mobile_id=tech_in.current_mobile_id,
        hire_date=tech_in.hire_date,
        notes=tech_in.notes
    )
    db.add(tech)
    db.commit()
    db.refresh(tech)
    return tech

@router.get("/{technician_id}/history")
def get_technician_history(technician_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    history = db.query(MobileTechnicianHistory).filter(
        MobileTechnicianHistory.technician_id == technician_id
    ).order_by(MobileTechnicianHistory.start_date.desc()).all()

    return [{
        "id": h.id,
        "mobile_id": h.mobile.id,
        "mobile_code": h.mobile.code,
        "role_in_mobile": h.role_in_mobile,
        "start_date": h.start_date.isoformat(),
        "end_date": h.end_date.isoformat() if h.end_date else None,
        "notes": h.notes
    } for h in history]
