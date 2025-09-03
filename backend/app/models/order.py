from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import enum

Base = declarative_base()

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# Modelo SQLAlchemy para la base de datos
class OrderDB(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), nullable=False)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    status = Column(String(50), default="pending")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

# Modelos Pydantic para la API
class OrderBase(BaseModel):
    customer_name: str
    product_name: str
    quantity: int
    price: float
    notes: Optional[str] = ""

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[OrderStatus] = None

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class Order(OrderBase):
    id: int
    total: float
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class OrderResponse(BaseModel):
    id: int
    customer_name: str
    product_name: str
    quantity: int
    price: float
    total: float
    status: str
    notes: str
    created_at: datetime
    
    class Config:
        orm_mode = True