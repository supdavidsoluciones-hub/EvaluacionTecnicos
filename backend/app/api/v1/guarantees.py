from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Guarantee, Order, Mobile, Technician, User
from backend.app.schemas.schemas import GuaranteeCreate, GuaranteeResponse
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/guarantees", tags=["Garantías"])

@router.get("", response_model=List[dict])
def list_guarantees(
    mobile_id: Optional[int] = None,
    technician_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    is_reincidence: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Guarantee)
    if mobile_id:
        query = query.filter(Guarantee.mobile_id == mobile_id)
    if technician_id:
        query = query.filter(Guarantee.technician_id == technician_id)
    if start_date:
        query = query.filter(Guarantee.guarantee_date >= start_date)
    if end_date:
        query = query.filter(Guarantee.guarantee_date <= end_date)
    if is_reincidence is not None:
        query = query.filter(Guarantee.is_reincidence == is_reincidence)

    guarantees = query.order_by(Guarantee.guarantee_date.desc()).all()
    return [{
        "id": g.id,
        "original_order_number": g.original_order_number,
        "guarantee_number": g.guarantee_number,
        "guarantee_date": g.guarantee_date.isoformat(),
        "mobile_id": g.mobile_id,
        "mobile_code": g.mobile.code if g.mobile else None,
        "technician_id": g.technician_id,
        "technician_name": g.technician.full_name if g.technician else None,
        "guarantee_type": g.guarantee_type,
        "cause": g.cause,
        "description": g.description,
        "is_reincidence": g.is_reincidence,
        "notes": g.notes
    } for g in guarantees]

@router.post("", response_model=GuaranteeResponse)
def create_guarantee(
    g_in: GuaranteeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_date = g_in.guarantee_date or date.today()
    guarantee = Guarantee(
        original_order_number=g_in.original_order_number,
        guarantee_number=g_in.guarantee_number,
        guarantee_date=target_date,
        mobile_id=g_in.mobile_id,
        technician_id=g_in.technician_id,
        guarantee_type=g_in.guarantee_type,
        cause=g_in.cause,
        description=g_in.description,
        is_reincidence=g_in.is_reincidence or False,
        notes=g_in.notes
    )
    db.add(guarantee)
    db.commit()
    db.refresh(guarantee)
    return guarantee

@router.get("/summary")
def get_guarantee_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Por defecto, resumen del mes actual o global
    mobiles = db.query(Mobile).order_by(Mobile.code.asc()).all()
    
    summary_by_mobile = []
    total_orders_global = 0
    total_guarantees_global = 0

    for m in mobiles:
        orders_q = db.query(Order).filter(Order.mobile_id == m.id, Order.status == "Completada")
        guarantees_q = db.query(Guarantee).filter(Guarantee.mobile_id == m.id)

        if start_date:
            orders_q = orders_q.filter(Order.order_date >= start_date)
            guarantees_q = guarantees_q.filter(Guarantee.guarantee_date >= start_date)
        if end_date:
            orders_q = orders_q.filter(Order.order_date <= end_date)
            guarantees_q = guarantees_q.filter(Guarantee.guarantee_date <= end_date)

        completed_orders = orders_q.count()
        guarantees_count = guarantees_q.count()
        reincidences_count = guarantees_q.filter(Guarantee.is_reincidence == True).count()

        guarantee_index = round((guarantees_count / completed_orders * 100), 2) if completed_orders > 0 else 0.0
        exceeds_target = (guarantee_index > 5.0)

        total_orders_global += completed_orders
        total_guarantees_global += guarantees_count

        summary_by_mobile.append({
            "mobile_id": m.id,
            "mobile_code": m.code,
            "completed_orders": completed_orders,
            "guarantees_count": guarantees_count,
            "reincidences_count": reincidences_count,
            "guarantee_index_pct": guarantee_index,
            "exceeds_target": exceeds_target  # Alerta roja si > 5%
        })

    overall_index = round((total_guarantees_global / total_orders_global * 100), 2) if total_orders_global > 0 else 0.0

    return {
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "total_completed_orders": total_orders_global,
        "total_guarantees": total_guarantees_global,
        "overall_guarantee_index_pct": overall_index,
        "target_pct": 5.0,
        "is_within_target": overall_index <= 5.0,
        "summary_by_mobile": summary_by_mobile
    }
