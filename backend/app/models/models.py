from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Text, Float, ForeignKey
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # 'Admin', 'Supervisor'

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    role = relationship("Role", back_populates="users")
    inspections = relationship("Inspection", back_populates="supervisor")


class Mobile(Base):
    __tablename__ = "mobiles"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)  # 'M200', 'M201', etc.
    vehicle_model = Column(String(60), default="Chevrolet P900", nullable=True)  # Chevrolet P900
    plate = Column(String(20), nullable=True)   # Placa del vehículo
    zone = Column(String(40), nullable=True)    # 'Chiriquí' o 'Santiago'
    color = Column(String(30), default="blanco", nullable=True)
    status = Column(String(30), default="activa")  # 'activa', 'mantenimiento', 'inactiva'
    cleanliness_status = Column(String(50), default="Limpio")
    damage_status = Column(String(50), default="Sin daños")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    technicians = relationship("Technician", back_populates="current_mobile", foreign_keys="[Technician.current_mobile_id]")
    history = relationship("MobileTechnicianHistory", back_populates="mobile")
    orders = relationship("Order", back_populates="mobile")
    inspections = relationship("Inspection", back_populates="mobile")
    guarantees = relationship("Guarantee", back_populates="mobile")
    action_plans = relationship("ActionPlan", back_populates="mobile")
    inventory = relationship("VehicleInventory", back_populates="mobile", cascade="all, delete-orphan")


class Technician(Base):
    __tablename__ = "technicians"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    status = Column(String(30), default="activo")  # 'activo', 'inactivo'
    current_mobile_id = Column(Integer, ForeignKey("mobiles.id"), nullable=True)
    hire_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    current_mobile = relationship("Mobile", back_populates="technicians", foreign_keys=[current_mobile_id])
    mobile_history = relationship("MobileTechnicianHistory", back_populates="technician")
    primary_orders = relationship("Order", back_populates="primary_technician", foreign_keys="[Order.primary_technician_id]")
    secondary_orders = relationship("Order", back_populates="secondary_technician", foreign_keys="[Order.secondary_technician_id]")
    inspections = relationship("Inspection", back_populates="technician")
    guarantees = relationship("Guarantee", back_populates="technician")


class MobileTechnicianHistory(Base):
    __tablename__ = "mobile_technician_history"

    id = Column(Integer, primary_key=True, index=True)
    mobile_id = Column(Integer, ForeignKey("mobiles.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    role_in_mobile = Column(String(30), default="principal")  # 'principal', 'auxiliar'
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    mobile = relationship("Mobile", back_populates="history")
    technician = relationship("Technician", back_populates="mobile_history")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), index=True, nullable=False)
    order_date = Column(Date, default=date.today, index=True, nullable=False)
    mobile_id = Column(Integer, ForeignKey("mobiles.id"), nullable=False)
    primary_technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    secondary_technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=True)
    order_type = Column(String(50), nullable=False)  # 'Instalación', 'Mantenimiento', 'Avería', etc.
    
    assignment_time = Column(String(10), nullable=True)  # HH:MM
    arrival_time = Column(String(10), nullable=True)     # HH:MM
    start_time = Column(String(10), nullable=True)       # HH:MM
    end_time = Column(String(10), nullable=True)         # HH:MM
    
    duration_minutes = Column(Integer, default=0)
    exceeds_target_time = Column(Boolean, default=False)  # True si Instalación > 45 min
    
    status = Column(String(30), default="Completada")     # 'Asignada', 'En camino', 'Completada', 'Cancelada'
    result = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    mobile = relationship("Mobile", back_populates="orders")
    primary_technician = relationship("Technician", back_populates="primary_orders", foreign_keys=[primary_technician_id])
    secondary_technician = relationship("Technician", back_populates="secondary_orders", foreign_keys=[secondary_technician_id])
    inspection = relationship("Inspection", back_populates="order", uselist=False)


class InspectionCategory(Base):
    __tablename__ = "inspection_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), nullable=False)  # 'SEGURIDAD', 'ACOMETIDA', 'CONECTORES FTTH', etc.
    code = Column(String(20), unique=True, nullable=False)
    sort_order = Column(Integer, default=0)

    checklist_items = relationship("InspectionChecklistTemplate", back_populates="category")


class InspectionChecklistTemplate(Base):
    __tablename__ = "inspection_checklist_template"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("inspection_categories.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    category = relationship("InspectionCategory", back_populates="checklist_items")


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)
    inspection_code = Column(String(30), unique=True, index=True, nullable=False)
    inspection_date = Column(Date, default=date.today, index=True, nullable=False)
    mobile_id = Column(Integer, ForeignKey("mobiles.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    order_number = Column(String(50), nullable=False)
    order_type = Column(String(50), nullable=False)
    
    general_result = Column(String(30), default="Cumple")  # 'Cumple', 'Cumple parcialmente', 'No cumple'
    observations = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    mobile = relationship("Mobile", back_populates="inspections")
    technician = relationship("Technician", back_populates="inspections")
    order = relationship("Order", back_populates="inspection")
    supervisor = relationship("User", back_populates="inspections")
    
    items = relationship("InspectionItem", back_populates="inspection", cascade="all, delete-orphan")
    photos = relationship("InspectionPhoto", back_populates="inspection", cascade="all, delete-orphan")
    non_conformities = relationship("NonConformity", back_populates="inspection")


class InspectionItem(Base):
    __tablename__ = "inspection_items"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("inspection_checklist_template.id"), nullable=True)
    category_name = Column(String(80), nullable=False)
    question_text = Column(Text, nullable=False)
    result = Column(String(20), nullable=False)  # 'Cumple', 'No cumple', 'No aplica'
    notes = Column(Text, nullable=True)

    inspection = relationship("Inspection", back_populates="items")


class InspectionPhoto(Base):
    __tablename__ = "inspection_photos"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    photo_url = Column(Text, nullable=False)
    s3_key = Column(String(255), nullable=True)
    photo_type = Column(String(50), nullable=True)
    caption = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    inspection = relationship("Inspection", back_populates="photos")


class NonConformity(Base):
    __tablename__ = "non_conformities"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    mobile_id = Column(Integer, ForeignKey("mobiles.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    category_name = Column(String(80), nullable=False)
    description = Column(Text, nullable=False)
    photo_url = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    responsible_person = Column(String(100), nullable=True)
    status = Column(String(30), default="Abierta")  # 'Abierta', 'En proceso', 'Corregida', 'Cerrada'
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    inspection = relationship("Inspection", back_populates="non_conformities")


class Guarantee(Base):
    __tablename__ = "guarantees"

    id = Column(Integer, primary_key=True, index=True)
    original_order_number = Column(String(50), nullable=False)
    guarantee_number = Column(String(50), index=True, nullable=False)
    guarantee_date = Column(Date, default=date.today, index=True, nullable=False)
    mobile_id = Column(Integer, ForeignKey("mobiles.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    guarantee_type = Column(String(80), nullable=False)
    cause = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_reincidence = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    mobile = relationship("Mobile", back_populates="guarantees")
    technician = relationship("Technician", back_populates="guarantees")


class ActionPlan(Base):
    __tablename__ = "action_plans"

    id = Column(Integer, primary_key=True, index=True)
    mobile_id = Column(Integer, ForeignKey("mobiles.id"), nullable=False)
    detected_problem = Column(Text, nullable=False)
    corrective_action = Column(Text, nullable=False)
    responsible_person = Column(String(100), nullable=False)
    start_date = Column(Date, default=date.today, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String(30), default="Pendiente")  # 'Pendiente', 'En proceso', 'Completado', 'Vencido'
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    mobile = relationship("Mobile", back_populates="action_plans")
    evidences = relationship("ActionPlanEvidence", back_populates="action_plan", cascade="all, delete-orphan")


class ActionPlanEvidence(Base):
    __tablename__ = "action_plan_evidence"

    id = Column(Integer, primary_key=True, index=True)
    action_plan_id = Column(Integer, ForeignKey("action_plans.id"), nullable=False)
    photo_url = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    action_plan = relationship("ActionPlan", back_populates="evidences")


class VehicleInventory(Base):
    """Inventario de herramientas por vehículo."""
    __tablename__ = "vehicle_inventory"

    id = Column(Integer, primary_key=True, index=True)
    mobile_id = Column(Integer, ForeignKey("mobiles.id"), nullable=False)
    tool_name = Column(String(120), nullable=False)       # Nombre de la herramienta
    category = Column(String(60), nullable=True)          # 'Herramienta', 'EPP', 'Stock', 'Seguridad'
    quantity_required = Column(Integer, default=1)        # Cantidad mínima requerida
    quantity_current = Column(Integer, default=0)         # Cantidad actual disponible
    status = Column(String(20), default="ok")             # 'ok', 'faltante', 'danado'
    serial_number = Column(String(80), nullable=True)     # Para equipos como fusionadora, OTDR
    notes = Column(Text, nullable=True)
    last_verified = Column(DateTime, nullable=True)       # Última vez verificada
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    mobile = relationship("Mobile", back_populates="inventory")
