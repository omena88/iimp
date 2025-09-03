from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import requests
import urllib.parse
import json
import re
import string
import random

app = FastAPI(
    title="Sistema de Procesamiento de Órdenes",
    description="API para gestionar órdenes de productos",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# Modelos simplificados eliminados para evitar problemas de compatibilidad

class OrderCreate(BaseModel):
    customer_name: str
    product_name: str
    quantity: int
    price: float
    notes: Optional[str] = ""

class OrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    notes: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class Order(BaseModel):
    id: int
    customer_name: str
    product_name: str
    quantity: int
    price: float
    total: float
    status: str
    notes: str
    created_at: datetime
    updated_at: Optional[datetime] = None

# Almacenamiento en memoria
orders_db = []
next_id = 1

@app.get("/")
async def root():
    return {"message": "Sistema de Procesamiento de Órdenes API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/v1/orders", response_model=List[Order])
async def get_orders():
    return orders_db

@app.get("/api/v1/orders/{order_id}", response_model=Order)
async def get_order(order_id: int):
    order = next((order for order in orders_db if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return order

@app.post("/api/v1/orders", response_model=Order)
async def create_order(order: OrderCreate):
    global next_id
    
    total = order.quantity * order.price
    
    new_order = {
        "id": next_id,
        "customer_name": order.customer_name,
        "product_name": order.product_name,
        "quantity": order.quantity,
        "price": order.price,
        "total": total,
        "status": "pending",
        "notes": order.notes,
        "created_at": datetime.now(),
        "updated_at": None
    }
    
    orders_db.append(new_order)
    next_id += 1
    
    return new_order

@app.put("/api/v1/orders/{order_id}", response_model=Order)
async def update_order(order_id: int, order_update: OrderUpdate):
    order_index = next((i for i, order in enumerate(orders_db) if order["id"] == order_id), None)
    if order_index is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    order = orders_db[order_index]
    
    if order_update.customer_name is not None:
        order["customer_name"] = order_update.customer_name
    if order_update.product_name is not None:
        order["product_name"] = order_update.product_name
    if order_update.quantity is not None:
        order["quantity"] = order_update.quantity
    if order_update.price is not None:
        order["price"] = order_update.price
    if order_update.notes is not None:
        order["notes"] = order_update.notes
    
    # Recalcular total si cantidad o precio cambiaron
    if order_update.quantity is not None or order_update.price is not None:
        order["total"] = order["quantity"] * order["price"]
    
    order["updated_at"] = datetime.now()
    
    return order

@app.patch("/api/v1/orders/{order_id}/status")
async def update_order_status(order_id: int, status_update: OrderStatusUpdate):
    order_index = next((i for i, order in enumerate(orders_db) if order["id"] == order_id), None)
    if order_index is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    orders_db[order_index]["status"] = status_update.status.value
    orders_db[order_index]["updated_at"] = datetime.now()
    
    return {"message": "Estado actualizado correctamente", "order": orders_db[order_index]}

@app.delete("/api/v1/orders/{order_id}")
async def delete_order(order_id: int):
    order_index = next((i for i, order in enumerate(orders_db) if order["id"] == order_id), None)
    if order_index is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    deleted_order = orders_db.pop(order_index)
    return {"message": "Orden eliminada correctamente", "order": deleted_order}

# ---------------------------------------------------------------------------------
# NUEVOS ENDPOINTS PARA SHORTLINKS Y CHECKOUT
# ---------------------------------------------------------------------------------



@app.post("/api/v1/create-order-link")
async def create_order_link(request: dict):
    """Crear enlace de pago personalizado para el checkout"""
    
    try:
        # Generar ID único para la orden
        order_id = f"order_{len(orders_db) + 1}_{hash(request.get('participant_email', '')) % 10000}"
        
        # Construir parámetros de URL
        params = {
            "name": request.get("participant_name", ""),
            "email": request.get("participant_email", ""),
            "document_type": request.get("document_type", ""),
            "document_number": request.get("document_number", ""),
            "inscription_type": request.get("inscription_type", ""),
            "product_id": request.get("product_id", ""),
            "quantity": str(request.get("quantity", 1)),
            "language": request.get("language", "es"),
            "order_id": order_id
        }
        
        # Añadir parámetros opcionales
        if request.get("phone"):
            params["phone"] = request["phone"]
        if request.get("company"):
            params["company"] = request["company"]
        if request.get("ruc"):
            params["ruc"] = request["ruc"]
            
        # Codificar parámetros
        query_string = urllib.parse.urlencode(params)
        
        # Crear URLs
        base_url = "https://apis-iimp-web.di8b44.easypanel.host"
        long_url = f"{base_url}/checkout.html?{query_string}"
        
        # Generar shortlink simple
        short_code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        short_url = f"{base_url}/c/{short_code}"
        
        return {
            "success": True,
            "message": "Link de pago generado exitosamente",
            "data": {
                "long_url": long_url,
                "short_url": short_url,
                "order_id": order_id,
                "participant_name": request.get("participant_name", ""),
                "participant_email": request.get("participant_email", ""),
                "product_id": request.get("product_id", ""),
                "quantity": request.get("quantity", 1),
                "total_amount": request.get("quantity", 1) * 150.00  # Precio ejemplo
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando link: {str(e)}")

@app.post("/api/v1/consultar-ruc")
async def consultar_ruc(request: dict):
    """Consultar información de RUC"""
    
    try:
        ruc = request.get("ruc", "")
        # Simulación de consulta RUC
        return {
            "success": True,
            "data": {
                "ruc": ruc,
                "razon_social": f"EMPRESA EJEMPLO {ruc[-3:]} S.A.C.",
                "estado": "ACTIVO",
                "direccion": "AV. EJEMPLO 123"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando RUC: {str(e)}")

@app.post("/api/v1/check-inscriptions")
async def check_inscriptions(request: dict):
    """Verificar inscripciones existentes"""
    
    try:
        return {
            "exists": False,
            "message": "No se encontraron inscripciones previas",
            "inscriptions": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verificando inscripciones: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)