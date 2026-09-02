from typing import List, Optional
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import (
    Mobile, Order, Inspection, NonConformity, Guarantee, ActionPlan, User
)
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard y Semáforos"])

@router.get("/summary")
def get_dashboard_summary(
    target_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sel_date = target_date or date.today()
    total_mobiles = db.query(Mobile).count()

    total_orders = db.query(Order).count()
    completed_orders = db.query(Order).filter(Order.status == "Completada").count()
    pending_orders = db.query(Order).filter(Order.status.in_(["Asignada", "En camino", "En sitio"])).count()

    total_inspections = db.query(Inspection).count()
    total_guarantees = db.query(Guarantee).count()

    guarantee_index_pct = round((total_guarantees / completed_orders * 100), 2) if completed_orders > 0 else 0.0

    # Tiempo promedio de instalaciones
    installations = db.query(Order).filter(
        Order.order_type == "Instalación",
        Order.status == "Completada",
        Order.duration_minutes > 0
    ).all()
    avg_install_time = round(sum(i.duration_minutes for i in installations) / len(installations), 1) if installations else 0.0

    return {
        "date": sel_date.isoformat(),
        "total_mobiles": total_mobiles,
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "pending_orders": pending_orders,
        "total_inspections": total_inspections,
        "total_guarantees": total_guarantees,
        "guarantee_index_pct": guarantee_index_pct,
        "guarantee_target_pct": 5.0,
        "avg_installation_time_minutes": avg_install_time
    }

@router.get("/mobile-status")
def get_mobile_status_semaphores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    mobiles = db.query(Mobile).order_by(Mobile.code.asc()).all()
    result = []

    for m in mobiles:
        completed = db.query(Order).filter(Order.mobile_id == m.id, Order.status == "Completada").count()
        total_m_orders = db.query(Order).filter(Order.mobile_id == m.id).count()
        compliance_pct = round((completed / total_m_orders * 100), 1) if total_m_orders > 0 else 100.0

        guarantees_count = db.query(Guarantee).filter(Guarantee.mobile_id == m.id).count()
        guarantee_index = round((guarantees_count / completed * 100), 2) if completed > 0 else 0.0

        inspections_count = db.query(Inspection).filter(Inspection.mobile_id == m.id).count()
        non_conformities_count = db.query(NonConformity).filter(NonConformity.mobile_id == m.id, NonConformity.status != "Cerrada").count()

        exceeds_time_count = db.query(Order).filter(
            Order.mobile_id == m.id,
            Order.order_type == "Instalación",
            Order.exceeds_target_time == True
        ).count()

        # Evaluación del Semáforo
        # 🔴 Rojo: Garantías > 5% O más de 3 No Conformidades abiertas O cumplimiento < 75%
        # 🟡 Amarillo: Garantías entre 3.5% y 5% O entre 1 y 3 No Conformidades O cumplimiento 75-85%
        # 🟢 Verde: Garantías <= 3.5%, No conformidades = 0, cumplimiento > 85%
        if guarantee_index > 5.0 or non_conformities_count >= 3 or compliance_pct < 75.0:
            semaphore_color = "red"
            status_text = "Requiere acción inmediata"
        elif guarantee_index >= 3.5 or non_conformities_count >= 1 or compliance_pct < 85.0:
            semaphore_color = "yellow"
            status_text = "Requiere seguimiento"
        else:
            semaphore_color = "green"
            status_text = "Buen desempeño"

        # Obtener técnicos activos
        active_techs = [h.technician.full_name for h in m.history if h.end_date is None]

        result.append({
            "mobile_id": m.id,
            "mobile_code": m.code,
            "assigned_technicians": active_techs,
            "total_orders": total_m_orders,
            "completed_orders": completed,
            "compliance_pct": compliance_pct,
            "guarantees_count": guarantees_count,
            "guarantee_index_pct": guarantee_index,
            "inspections_count": inspections_count,
            "open_non_conformities": non_conformities_count,
            "exceeds_target_time_count": exceeds_time_count,
            "semaphore_color": semaphore_color,
            "status_text": status_text
        })

    return result

@router.get("/ranking")
def get_mobile_ranking(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    status_list = get_mobile_status_semaphores(db=db, current_user=current_user)
    
    # Algoritmo de Puntuación Global (Score out of 100):
    # Score = (Cumplimiento * 0.4) + (100 - (IndiceGarantias * 10)) * 0.4 + (100 - (NC_abiertas * 15)) * 0.2
    for item in status_list:
        score = (item["compliance_pct"] * 0.4) + max(0, (100 - item["guarantee_index_pct"] * 10)) * 0.4 + max(0, (100 - item["open_non_conformities"] * 15)) * 0.2
        item["overall_score"] = round(score, 1)

    sorted_ranking = sorted(status_list, key=lambda x: x["overall_score"], reverse=True)
    
    for idx, item in enumerate(sorted_ranking, 1):
        item["rank"] = idx

    return sorted_ranking

@router.get("/alerts")
def get_system_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    alerts = []
    
    # 1. Alertas por Móviles con Garantías > 5%
    mobiles_status = get_mobile_status_semaphores(db=db, current_user=current_user)
    for m in mobiles_status:
        if m["guarantee_index_pct"] > 5.0:
            alerts.append({
                "level": "danger",
                "code": "HIGH_GUARANTEE_INDEX",
                "title": f"Móvil {m['mobile_code']} supera límite de garantías",
                "message": f"Índice de garantías actual: {m['guarantee_index_pct']}% (Meta: <= 5.0%).",
                "mobile_code": m["mobile_code"]
            })
        elif m["guarantee_index_pct"] >= 4.0:
            alerts.append({
                "level": "warning",
                "code": "WARN_GUARANTEE_INDEX",
                "title": f"Móvil {m['mobile_code']} cercana al límite de garantías",
                "message": f"Índice de garantías actual: {m['guarantee_index_pct']}% (Meta: <= 5.0%).",
                "mobile_code": m["mobile_code"]
            })

        if m["exceeds_target_time_count"] >= 3:
            alerts.append({
                "level": "danger",
                "code": "TIME_EXCEEDED",
                "title": f"Móvil {m['mobile_code']} con excesos de tiempo",
                "message": f"{m['exceeds_target_time_count']} instalaciones superaron los 45 minutos.",
                "mobile_code": m["mobile_code"]
            })

        if m["open_non_conformities"] > 0:
            alerts.append({
                "level": "warning",
                "code": "OPEN_NON_CONFORMITIES",
                "title": f"Móvil {m['mobile_code']} con No Conformidades pendientes",
                "message": f"Tiene {m['open_non_conformities']} no conformidades abiertas.",
                "mobile_code": m["mobile_code"]
            })

    return alerts
