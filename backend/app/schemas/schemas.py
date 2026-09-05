from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user_info: dict

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    role_id: int

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role_id: int
    is_active: bool

    class Config:
        from_attributes = True

# Mobile Schemas
class MobileCreate(BaseModel):
    code: str
    vehicle_model: Optional[str] = "Chevrolet P900"
    plate: Optional[str] = None
    zone: Optional[str] = None
    color: Optional[str] = "blanco"
    status: Optional[str] = "activa"
    cleanliness_status: Optional[str] = "Limpio"
    damage_status: Optional[str] = "Sin daños"
    notes: Optional[str] = None

class MobileUpdate(BaseModel):
    vehicle_model: Optional[str] = None
    plate: Optional[str] = None
    zone: Optional[str] = None
    color: Optional[str] = None
    status: Optional[str] = None
    cleanliness_status: Optional[str] = None
    damage_status: Optional[str] = None
    notes: Optional[str] = None

class MobileResponse(BaseModel):
    id: int
    code: str
    vehicle_model: Optional[str] = None
    plate: Optional[str] = None
    zone: Optional[str] = None
    color: Optional[str] = None
    status: str
    cleanliness_status: str
    damage_status: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AssignTechniciansRequest(BaseModel):
    primary_technician_id: int
    secondary_technician_id: Optional[int] = None
    notes: Optional[str] = None

# Technician Schemas
class TechnicianCreate(BaseModel):
    full_name: str
    status: Optional[str] = "activo"
    current_mobile_id: Optional[int] = None
    hire_date: Optional[date] = None
    notes: Optional[str] = None

class TechnicianResponse(BaseModel):
    id: int
    full_name: str
    status: str
    current_mobile_id: Optional[int] = None
    hire_date: Optional[date] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True

# Order Schemas
class OrderCreate(BaseModel):
    order_number: str
    order_date: Optional[date] = None
    mobile_id: int
    primary_technician_id: int
    secondary_technician_id: Optional[int] = None
    order_type: str
    assignment_time: Optional[str] = None
    arrival_time: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = "Completada"
    result: Optional[str] = None
    notes: Optional[str] = None

class OrderResponse(BaseModel):
    id: int
    order_number: str
    order_date: date
    mobile_id: int
    primary_technician_id: int
    secondary_technician_id: Optional[int] = None
    order_type: str
    assignment_time: Optional[str] = None
    arrival_time: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: int
    exceeds_target_time: bool
    status: str
    result: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True

# Inspection Schemas
class InspectionItemCreate(BaseModel):
    template_id: Optional[int] = None
    category_name: str
    question_text: str
    result: str  # 'Cumple', 'No cumple', 'No aplica'
    notes: Optional[str] = None

class InspectionCreate(BaseModel):
    inspection_date: Optional[date] = None
    mobile_id: int
    technician_id: int
    order_number: str
    order_type: str
    general_result: Optional[str] = "Cumple"
    observations: Optional[str] = None
    corrective_action: Optional[str] = None
    items: List[InspectionItemCreate]

class InspectionResponse(BaseModel):
    id: int
    inspection_code: str
    inspection_date: date
    mobile_id: int
    technician_id: int
    order_number: str
    order_type: str
    general_result: str
    observations: Optional[str] = None
    corrective_action: Optional[str] = None
    supervisor_id: int

    class Config:
        from_attributes = True

# Guarantee Schemas
class GuaranteeCreate(BaseModel):
    original_order_number: str
    guarantee_number: str
    guarantee_date: Optional[date] = None
    mobile_id: int
    technician_id: int
    guarantee_type: str
    cause: str
    description: Optional[str] = None
    is_reincidence: Optional[bool] = False
    notes: Optional[str] = None

class GuaranteeResponse(BaseModel):
    id: int
    original_order_number: str
    guarantee_number: str
    guarantee_date: date
    mobile_id: int
    technician_id: int
    guarantee_type: str
    cause: str
    description: Optional[str] = None
    is_reincidence: bool
    notes: Optional[str] = None

    class Config:
        from_attributes = True

# Action Plan Schemas
class ActionPlanCreate(BaseModel):
    mobile_id: int
    detected_problem: str
    corrective_action: str
    responsible_person: str
    start_date: Optional[date] = None
    due_date: date
    status: Optional[str] = "Pendiente"
    notes: Optional[str] = None

class ActionPlanResponse(BaseModel):
    id: int
    mobile_id: int
    detected_problem: str
    corrective_action: str
    responsible_person: str
    start_date: date
    due_date: date
    status: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True
