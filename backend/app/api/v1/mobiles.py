from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Mobile, Technician, MobileTechnicianHistory, User, VehicleInventory, Inspection, Order
from backend.app.schemas.schemas import MobileCreate, MobileUpdate, MobileResponse, AssignTechniciansRequest
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/mobiles", tags=["Móviles"])

# ──────────────────────────────────────────────────────────────────────────────
# LIST ALL MOBILES
# ──────────────────────────────────────────────────────────────────────────────
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
            tech = db.query(Technician).filter(Technician.id == h.technician_id).first()
            if tech:
                if h.role_in_mobile == "principal":
                    primary_tech = {"id": tech.id, "name": tech.full_name}
                elif h.role_in_mobile == "auxiliar":
                    secondary_tech = {"id": tech.id, "name": tech.full_name}

        # Inventory summary for quick display
        inv_count = db.query(VehicleInventory).filter(VehicleInventory.mobile_id == m.id).count()
        inv_issues = db.query(VehicleInventory).filter(
            VehicleInventory.mobile_id == m.id,
            VehicleInventory.status != "ok"
        ).count()

        result.append({
            "id": m.id,
            "code": m.code,
            "vehicle_model": m.vehicle_model or "Chevrolet P900",
            "plate": m.plate,
            "zone": m.zone,
            "color": m.color or "blanco",
            "status": m.status,
            "cleanliness_status": m.cleanliness_status or "Limpio",
            "damage_status": m.damage_status or "Sin daños",
            "notes": m.notes,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "primary_technician": primary_tech,
            "secondary_technician": secondary_tech,
            "inventory_total": inv_count,
            "inventory_issues": inv_issues,
        })
    return result


# ──────────────────────────────────────────────────────────────────────────────
# MOBILE PROFILE – full detail (technicians + inventory + recent inspections)
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/{mobile_id}/profile")
def get_mobile_profile(mobile_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    m = db.query(Mobile).filter(Mobile.id == mobile_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Móvil no encontrada")

    # Active technicians
    history_active = db.query(MobileTechnicianHistory).filter(
        MobileTechnicianHistory.mobile_id == mobile_id,
        MobileTechnicianHistory.end_date == None
    ).all()
    technicians = []
    for h in history_active:
        tech = db.query(Technician).filter(Technician.id == h.technician_id).first()
        if tech:
            technicians.append({
                "id": tech.id,
                "name": tech.full_name,
                "role": h.role_in_mobile,
                "since": h.start_date.isoformat() if h.start_date else None,
                "status": tech.status,
            })

    # Inventory
    inventory = []
    for item in db.query(VehicleInventory).filter(VehicleInventory.mobile_id == mobile_id).order_by(VehicleInventory.category, VehicleInventory.tool_name).all():
        inventory.append({
            "id": item.id,
            "tool_name": item.tool_name,
            "category": item.category,
            "quantity_required": item.quantity_required,
            "quantity_current": item.quantity_current,
            "status": item.status,
            "serial_number": item.serial_number,
            "notes": item.notes,
            "last_verified": item.last_verified.isoformat() if item.last_verified else None,
        })

    # Recent inspections (last 10)
    recent_inspections = db.query(Inspection).filter(
        Inspection.mobile_id == mobile_id
    ).order_by(Inspection.inspection_date.desc()).limit(10).all()
    inspections_list = []
    for insp in recent_inspections:
        tech = db.query(Technician).filter(Technician.id == insp.technician_id).first()
        inspections_list.append({
            "id": insp.id,
            "code": insp.inspection_code,
            "date": insp.inspection_date.isoformat(),
            "technician": tech.full_name if tech else "—",
            "order_number": insp.order_number,
            "order_type": insp.order_type,
            "result": insp.general_result,
        })

    # Stats
    total_orders = db.query(Order).filter(Order.mobile_id == mobile_id).count()
    total_inspections = db.query(Inspection).filter(Inspection.mobile_id == mobile_id).count()
    ok_inspections = db.query(Inspection).filter(
        Inspection.mobile_id == mobile_id,
        Inspection.general_result == "Cumple"
    ).count()

    return {
        "id": m.id,
        "code": m.code,
        "vehicle_model": m.vehicle_model or "Chevrolet P900",
        "plate": m.plate,
        "zone": m.zone,
        "color": m.color or "blanco",
        "status": m.status,
        "cleanliness_status": m.cleanliness_status or "Limpio",
        "damage_status": m.damage_status or "Sin daños",
        "notes": m.notes,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "technicians": technicians,
        "inventory": inventory,
        "recent_inspections": inspections_list,
        "stats": {
            "total_orders": total_orders,
            "total_inspections": total_inspections,
            "ok_inspections": ok_inspections,
            "quality_score": round((ok_inspections / total_inspections * 100) if total_inspections > 0 else 100),
        }
    }


# ──────────────────────────────────────────────────────────────────────────────
# CREATE MOBILE
# ──────────────────────────────────────────────────────────────────────────────
@router.post("", response_model=MobileResponse)
def create_mobile(mobile_in: MobileCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(Mobile).filter(Mobile.code == mobile_in.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"La móvil {mobile_in.code} ya existe")
    mobile = Mobile(
        code=mobile_in.code,
        vehicle_model=mobile_in.vehicle_model or "Chevrolet P900",
        plate=mobile_in.plate,
        zone=mobile_in.zone,
        color=mobile_in.color or "blanco",
        status=mobile_in.status,
        cleanliness_status=mobile_in.cleanliness_status or "Limpio",
        damage_status=mobile_in.damage_status or "Sin daños",
        notes=mobile_in.notes
    )
    db.add(mobile)
    db.commit()
    db.refresh(mobile)
    # Auto-seed default inventory tools for this new mobile
    _seed_default_inventory(mobile.id, db)
    return mobile


# ──────────────────────────────────────────────────────────────────────────────
# UPDATE MOBILE
# ──────────────────────────────────────────────────────────────────────────────
@router.put("/{mobile_id}")
def update_mobile(mobile_id: int, mobile_in: MobileUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    m = db.query(Mobile).filter(Mobile.id == mobile_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Móvil no encontrada")

    for field, value in mobile_in.dict(exclude_unset=True).items():
        setattr(m, field, value)

    db.commit()
    db.refresh(m)
    return {"message": f"Móvil {m.code} actualizada correctamente", "id": m.id, "code": m.code, "status": m.status}

# ──────────────────────────────────────────────────────────────────────────────
# DELETE MOBILE
# ──────────────────────────────────────────────────────────────────────────────
@router.delete("/{mobile_id}")
def delete_mobile(mobile_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    m = db.query(Mobile).filter(Mobile.id == mobile_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Móvil no encontrada")
    
    # Check if there are orders or inspections tied to this mobile before deletion
    if db.query(Order).filter(Order.mobile_id == mobile_id).count() > 0 or \
       db.query(Inspection).filter(Inspection.mobile_id == mobile_id).count() > 0:
        # Instead of hard delete, maybe just deactivate, or we can hard delete for now as requested
        pass
    
    db.delete(m)
    db.commit()
    return {"message": f"Móvil {m.code} eliminada correctamente"}


# ──────────────────────────────────────────────────────────────────────────────
# ASSIGN TECHNICIANS
# ──────────────────────────────────────────────────────────────────────────────
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

    now = datetime.utcnow()
    # Close existing active assignments for this mobile
    active_histories = db.query(MobileTechnicianHistory).filter(
        MobileTechnicianHistory.mobile_id == mobile_id,
        MobileTechnicianHistory.end_date == None
    ).all()
    for h in active_histories:
        h.end_date = now

    # Assign primary technician
    tech1 = db.query(Technician).filter(Technician.id == assign_data.primary_technician_id).first()
    if not tech1:
        raise HTTPException(status_code=404, detail="Técnico principal no encontrado")
    tech1.current_mobile_id = mobile_id
    db.add(MobileTechnicianHistory(
        mobile_id=mobile_id, technician_id=tech1.id, role_in_mobile="principal",
        start_date=now, assigned_by_user_id=current_user.id, notes=assign_data.notes
    ))

    # Assign secondary technician (optional)
    if assign_data.secondary_technician_id:
        tech2 = db.query(Technician).filter(Technician.id == assign_data.secondary_technician_id).first()
        if tech2:
            tech2.current_mobile_id = mobile_id
            db.add(MobileTechnicianHistory(
                mobile_id=mobile_id, technician_id=tech2.id, role_in_mobile="auxiliar",
                start_date=now, assigned_by_user_id=current_user.id, notes=assign_data.notes
            ))

    db.commit()
    return {"message": f"Técnicos asignados correctamente a móvil {mobile.code}"}


# ──────────────────────────────────────────────────────────────────────────────
# INVENTORY ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/{mobile_id}/inventory")
def get_inventory(mobile_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    m = db.query(Mobile).filter(Mobile.id == mobile_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Móvil no encontrada")
    items = db.query(VehicleInventory).filter(VehicleInventory.mobile_id == mobile_id).order_by(
        VehicleInventory.category, VehicleInventory.tool_name).all()
    return [{"id": i.id, "tool_name": i.tool_name, "category": i.category,
             "quantity_required": i.quantity_required, "quantity_current": i.quantity_current,
             "status": i.status, "serial_number": i.serial_number, "notes": i.notes,
             "last_verified": i.last_verified.isoformat() if i.last_verified else None} for i in items]


@router.put("/{mobile_id}/inventory/{item_id}")
def update_inventory_item(mobile_id: int, item_id: int, data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(VehicleInventory).filter(VehicleInventory.id == item_id, VehicleInventory.mobile_id == mobile_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ítem de inventario no encontrado")
    for field in ["quantity_current", "status", "notes", "serial_number"]:
        if field in data:
            setattr(item, field, data[field])
    item.last_verified = datetime.utcnow()
    db.commit()
    return {"message": "Inventario actualizado", "id": item.id}


@router.post("/{mobile_id}/inventory/seed")
def seed_inventory(mobile_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    m = db.query(Mobile).filter(Mobile.id == mobile_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Móvil no encontrada")
    added = _seed_default_inventory(mobile_id, db)
    return {"message": f"{added} herramientas agregadas al inventario de {m.code}"}


# ──────────────────────────────────────────────────────────────────────────────
# HISTORY
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/{mobile_id}/history")
def get_mobile_history(mobile_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    history = db.query(MobileTechnicianHistory).filter(
        MobileTechnicianHistory.mobile_id == mobile_id
    ).order_by(MobileTechnicianHistory.start_date.desc()).all()
    return [{
        "id": h.id,
        "technician_id": h.technician_id,
        "technician_name": db.query(Technician).filter(Technician.id == h.technician_id).first().full_name if db.query(Technician).filter(Technician.id == h.technician_id).first() else "—",
        "role_in_mobile": h.role_in_mobile,
        "start_date": h.start_date.isoformat(),
        "end_date": h.end_date.isoformat() if h.end_date else None,
        "notes": h.notes
    } for h in history]


def _seed_default_inventory(mobile_id: int, db: Session) -> int:
    default_tools = [
        # ── Herramientas Manuales ──────────────────────────────────────────────
        ("Alicate Corte Diagonal 7\"",         "Herramienta", 2),
        ("Alicate Punta 7\"",                  "Herramienta", 2),
        ("Alicate Universal 8\"",              "Herramienta", 2),
        ("Desatornillador Phillips",           "Herramienta", 2),
        ("Desatornillador Plano",              "Herramienta", 2),
        ("Llave Corofija 3/8",                 "Herramienta", 2),
        ("Llave Corofija 7/16",                "Herramienta", 2),
        ("Martillo Herramientas P/Móviles",    "Herramienta", 1),
        ("Bolso de Herramientas",              "Herramienta", 2),
        ("Caja de Herramientas",               "Herramienta", 1),
        ("Marco de Segueta",                   "Herramienta", 1),
        ("Extensión P/Pintor",                 "Herramienta", 1),
        ("Odómetro",                           "Herramienta", 1),
        ("Ratch de 3/8",                       "Herramienta", 1),
        ("Extensión para Rach de 3/8",         "Herramienta", 1),
        ("Cubo 3/8 x 5/8",                     "Herramienta", 1),
        ("Cubo para Rach 7/16",                "Herramienta", 1),
        ("Engrapadora T-59",                   "Herramienta", 1),
        ("Cureña",                             "Herramienta", 1),
        ("Sonda Pasa-Cable en Ductos 100 Mts / 6mm (60 mts)", "Herramienta", 1),
        # ── Herramientas Eléctricas ───────────────────────────────────────────
        ("Inversor de 1500 W / 1800 W",        "Eléctrico",   1),
        ("Multímetro Digital",                 "Eléctrico",   1),
        ("Extensión Eléctrica",                "Eléctrico",   1),
        ("Taladro Inalámbrico (de cable)",     "Eléctrico",   1),
        ("Cubo P/Taladro 3/8",                 "Eléctrico",   1),
        ("Broca P/Concreto 1/4",               "Eléctrico",   1),
        ("Broca P/Concreto 3/8",               "Eléctrico",   1),
        ("Broca 3/8\" Metal",                  "Eléctrico",   1),
        ("Brocas 5/16 x 12 Metal",             "Eléctrico",   1),
        # ── Fibra Óptica ──────────────────────────────────────────────────────
        ("Cleaver F.O Sumitomo (Cortadora F.O)", "Fibra Óptica", 2),
        ("Peladora Fibra 3 Calibres",          "Fibra Óptica", 2),
        ("Peladora Cable Drop",                "Fibra Óptica", 2),
        ("Regla para Cortador",                "Fibra Óptica", 2),
        ("Limpiador de Conectores One-Click (SC-2.5MM)", "Fibra Óptica", 2),
        ("Medidor de Potencia PON FTTH",       "Fibra Óptica", 1),
        ("Localizador Óptico de Falla Visual F.O [FFL-50/1]", "Fibra Óptica", 2),
        # ── EPP (Equipo de Protección Personal) ───────────────────────────────
        ("Arnés Rota Confort Faja Lumbar 3 Puntos", "EPP", 1),
        ("Casco de Seguridad",                 "EPP", 2),
        ("Línea de Vida Sencilla 90 30/49 Gancho Grande", "EPP", 1),
        ("Línea de Posicionamiento 14MM CU 31/1", "EPP", 1),
        ("Lente Protector Fuji2 [PO-FUJI2NOOR]", "EPP", 2),
        ("Lentes de Seguridad Claro",          "EPP", 2),
        ("Chaleco Seguridad Fosforescente",    "EPP", 2),
        ("Guante Protec. Palma Látex (A3) Par 10CM", "EPP", 2),
        ("Guante Protec. Palma Látex (A3) Par 8CM",  "EPP", 2),
        ("Foco de Minero",                     "EPP", 2),
        # ── Seguridad Vial ────────────────────────────────────────────────────
        ("Conos Reflectores 28\" P/Móviles",   "Seguridad", 4),
        ("Cadena Galvanizada P/Móviles",       "Seguridad", 2),
        ("Candado Segur P/Móviles 60MM",       "Seguridad", 2),
        ("Kit de Seguridad P/Móvil [12560]",   "Seguridad", 1),
        # ── Escaleras ─────────────────────────────────────────────────────────
        ("Escalera de Extensión #28 (con Ganchos)", "Escalera", 1),
        ("Escalera Recta 12 FT (Machillo)",    "Escalera", 1),
        ("Escalera de 6 Peldaños",             "Escalera", 1),
        # ── Telecom / Equipos ─────────────────────────────────────────────────
        ("Teléfono Pared P/Móvil",             "Telecom", 1),
        ("Televisor 24\" (o menor tamaño)",    "Telecom", 1),
        ("Laptop con Puerto de Red 1 GB",      "Telecom", 1),
        # ── Bolsos / Contenedores ─────────────────────────────────────────────
        ("Bolso Porta Herramientas",           "Herramienta", 2),
    ]
    added = 0
    for tool_name, category, qty_required in default_tools:
        exists = db.query(VehicleInventory).filter(
            VehicleInventory.mobile_id == mobile_id,
            VehicleInventory.tool_name == tool_name
        ).first()
        if not exists:
            db.add(VehicleInventory(
                mobile_id=mobile_id,
                tool_name=tool_name,
                category=category,
                quantity_required=qty_required,
                quantity_current=qty_required,
                status="ok"
            ))
            added += 1
    db.commit()
    return added

