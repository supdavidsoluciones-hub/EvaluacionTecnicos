from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Order, Mobile, Technician, User
from backend.app.schemas.schemas import OrderCreate, OrderResponse
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="", tags=["Órdenes y Producción"])

def parse_time_to_minutes(time_str: str) -> Optional[int]:
    if not time_str or ":" not in time_str:
        return None
    try:
        parts = time_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return None

def calculate_duration(start_str: str, end_str: str) -> int:
    start_min = parse_time_to_minutes(start_str)
    end_min = parse_time_to_minutes(end_str)
    if start_min is not None and end_min is not None:
        if end_min >= start_min:
            return end_min - start_min
        else:
            # Caso en que pase de medianoche
            return (1440 - start_min) + end_min
    return 0

@router.get("/orders", response_model=List[dict])
def list_orders(
    order_date: Optional[date] = None,
    mobile_id: Optional[int] = None,
    technician_id: Optional[int] = None,
    order_type: Optional[str] = None,
    status: Optional[str] = None,
    exceeds_target: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Order)
    if order_date:
        query = query.filter(Order.order_date == order_date)
    if mobile_id:
        query = query.filter(Order.mobile_id == mobile_id)
    if technician_id:
        query = query.filter(
            (Order.primary_technician_id == technician_id) | (Order.secondary_technician_id == technician_id)
        )
    if order_type:
        query = query.filter(Order.order_type == order_type)
    if status:
        query = query.filter(Order.status == status)
    if exceeds_target is not None:
        query = query.filter(Order.exceeds_target_time == exceeds_target)

    orders = query.order_by(Order.order_date.desc(), Order.id.desc()).all()
    
    result = []
    for o in orders:
        result.append({
            "id": o.id,
            "order_number": o.order_number,
            "order_date": o.order_date.isoformat(),
            "mobile_id": o.mobile_id,
            "mobile_code": o.mobile.code if o.mobile else None,
            "primary_technician_id": o.primary_technician_id,
            "primary_technician_name": o.primary_technician.full_name if o.primary_technician else None,
            "secondary_technician_id": o.secondary_technician_id,
            "secondary_technician_name": o.secondary_technician.full_name if o.secondary_technician else None,
            "order_type": o.order_type,
            "assignment_time": o.assignment_time,
            "arrival_time": o.arrival_time,
            "start_time": o.start_time,
            "end_time": o.end_time,
            "duration_minutes": o.duration_minutes,
            "exceeds_target_time": o.exceeds_target_time,
            "status": o.status,
            "result": o.result,
            "notes": o.notes,
            "has_inspection": o.inspection is not None
        })
    return result

@router.post("/orders", response_model=OrderResponse)
def create_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_date = order_in.order_date or date.today()
    duration = calculate_duration(order_in.start_time, order_in.end_time)
    
    # Evaluar regla de 45 minutos para Instalaciones
    exceeds = False
    if order_in.order_type == "Instalación" and duration > 45:
        exceeds = True

    order = Order(
        order_number=order_in.order_number,
        order_date=target_date,
        mobile_id=order_in.mobile_id,
        primary_technician_id=order_in.primary_technician_id,
        secondary_technician_id=order_in.secondary_technician_id,
        order_type=order_in.order_type,
        assignment_time=order_in.assignment_time,
        arrival_time=order_in.arrival_time,
        start_time=order_in.start_time,
        end_time=order_in.end_time,
        duration_minutes=duration,
        exceeds_target_time=exceeds,
        status=order_in.status or "Completada",
        result=order_in.result,
        notes=order_in.notes
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order

@router.post("/orders/bulk-import")
def bulk_import_orders(
    orders_list: List[OrderCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    created_count = 0
    for o_in in orders_list:
        target_date = o_in.order_date or date.today()
        duration = calculate_duration(o_in.start_time, o_in.end_time)
        exceeds = (o_in.order_type == "Instalación" and duration > 45)

        order = Order(
            order_number=o_in.order_number,
            order_date=target_date,
            mobile_id=o_in.mobile_id,
            primary_technician_id=o_in.primary_technician_id,
            secondary_technician_id=o_in.secondary_technician_id,
            order_type=o_in.order_type,
            assignment_time=o_in.assignment_time,
            arrival_time=o_in.arrival_time,
            start_time=o_in.start_time,
            end_time=o_in.end_time,
            duration_minutes=duration,
            exceeds_target_time=exceeds,
            status=o_in.status or "Completada",
            result=o_in.result,
            notes=o_in.notes
        )
        db.add(order)
        created_count += 1
    
    db.commit()
    return {"message": f"Se importaron {created_count} órdenes correctamente"}

@router.get("/production/daily-summary")
def get_daily_production_summary(
    target_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    selected_date = target_date or date.today()
    mobiles = db.query(Mobile).order_by(Mobile.code.asc()).all()
    
    summary = []
    total_assigned_all = 0
    total_completed_all = 0

    for m in mobiles:
        orders_m = db.query(Order).filter(
            Order.mobile_id == m.id,
            Order.order_date == selected_date
        ).all()

        assigned = len(orders_m)
        completed = sum(1 for o in orders_m if o.status == "Completada")
        pending = sum(1 for o in orders_m if o.status in ["Asignada", "En camino", "En sitio", "Reprogramada"])
        cancelled = sum(1 for o in orders_m if o.status in ["Cancelada", "No realizada"])
        
        pct_cumplimiento = round((completed / assigned * 100), 1) if assigned > 0 else 0.0

        total_assigned_all += assigned
        total_completed_all += completed

        summary.append({
            "mobile_id": m.id,
            "mobile_code": m.code,
            "assigned": assigned,
            "completed": completed,
            "pending": pending,
            "cancelled": cancelled,
            "compliance_pct": pct_cumplimiento
        })

    overall_pct = round((total_completed_all / total_assigned_all * 100), 1) if total_assigned_all > 0 else 0.0

    return {
        "date": selected_date.isoformat(),
        "summary_by_mobile": summary,
        "overall_assigned": total_assigned_all,
        "overall_completed": total_completed_all,
        "overall_compliance_pct": overall_pct
    }
