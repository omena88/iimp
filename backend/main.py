from fastapi import FastAPI, HTTPException, UploadFile, File, Form
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
import asyncio
from fastapi.responses import RedirectResponse

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

# Base de datos simple en memoria para enlaces cortos
short_links_db = {}

# Función para crear enlaces cortos con TinyURL
async def create_tinyurl(long_url: str) -> str:
    """Crear enlace corto usando TinyURL API"""
    try:
        # Intentar usar TinyURL
        tinyurl_api = f"http://tinyurl.com/api-create.php?url={urllib.parse.quote(long_url)}"
        response = requests.get(tinyurl_api, timeout=5)
        
        if response.status_code == 200 and response.text.startswith('http'):
            return response.text.strip()
        else:
            # Si TinyURL falla, crear enlace corto local como respaldo
            return create_local_shortlink(long_url)
            
    except Exception as e:
        print(f"Error con TinyURL: {e}")
        # Si hay error, crear enlace corto local como respaldo
        return create_local_shortlink(long_url)

def create_local_shortlink(long_url: str) -> str:
    """Crear enlace corto local como respaldo"""
    short_code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    base_url = "https://apis-iimp-web.di8b44.easypanel.host"
    short_url = f"{base_url}/c/{short_code}"
    
    # Guardar en base de datos local
    short_links_db[short_code] = long_url
    
    return short_url

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



# IDs de productos hardcodeados desde productos.md
PRODUCT_IDS = {
    "CONVENCIONISTA_ASOCIADO_SME": 150,
    "CONVENCIONISTA_DOCENTE": 151,
    "CONVENCIONISTA_ESTUDIANTE": 152,
    "CONVENCIONISTA_NO_ASOCIADO": 154,
    "CONVENCIONISTA_ASOCIADO_ACTIVO": 155,
    "EXTEMIN_WEEK": 158
}

@app.post("/api/v1/create-order-link")
async def create_order_link(request: dict):
    """Crear enlace de pago personalizado para el checkout"""
    
    try:
        # Validar que se proporcionen los campos requeridos
        required_fields = ["product_id", "email", "nombres", "apellidos", "celular", "tipo_documento", "numero_documento"]
        for field in required_fields:
            if not request.get(field):
                raise HTTPException(status_code=400, detail=f"Campo requerido faltante: {field}")
        
        # Validar que el product_id sea válido
        product_id = request.get("product_id")
        if product_id not in PRODUCT_IDS.values():
            raise HTTPException(status_code=400, detail=f"Product ID inválido: {product_id}")
        
        # Generar ID único para la orden
        order_id = f"order_{len(orders_db) + 1}_{hash(request.get('email', '')) % 10000}"
        
        # Construir parámetros de URL usando los nombres exactos del request
        params = {
            "name": f"{request.get('nombres', '')} {request.get('apellidos', '')}".strip(),
            "email": request.get("email", ""),
            "document_type": request.get("tipo_documento", ""),
            "document_number": request.get("numero_documento", ""),
            "phone": request.get("celular", ""),
            "product_id": str(product_id),
            "quantity": "1",
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
        
        # Generar shortlink usando TinyURL
        short_url = await create_tinyurl(long_url)
        
        return {
            "success": True,
            "message": "Link de pago generado exitosamente",
            "data": {
                "long_url": long_url,
                "short_url": short_url,
                "order_id": order_id,
                "product_id": product_id,
                "email": request.get("email", ""),
                "nombres": request.get("nombres", ""),
                "apellidos": request.get("apellidos", ""),
                "celular": request.get("celular", ""),
                "tipo_documento": request.get("tipo_documento", ""),
                "numero_documento": request.get("numero_documento", "")
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando link: {str(e)}")

@app.post("/api/v1/consultar-ruc")
async def consultar_ruc(request: dict):
    """Consultar información de RUC usando API de ruc.com.pe"""
    import httpx
    
    try:
        ruc = request.get("ruc", "")
        
        if not ruc or len(ruc) != 11 or not ruc.isdigit():
            raise HTTPException(status_code=400, detail="RUC debe tener 11 dígitos")
        
        # Consultar API real de ruc.com.pe
        api_url = "https://ruc.com.pe/api/v1/consultas"
        payload = {
            "token": "ef5e49a4-f4e1-4928-bb01-064e522a4a85-49610454-2d87-4152-bfe6-2f7cd19f86c1",
            "ruc": ruc
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(api_url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    return {
                        "success": True,
                        "razonSocial": result.get("nombre_o_razon_social", ""),
                        "ruc": result.get("ruc", ruc),
                        "estado": result.get("estado_del_contribuyente", "")
                    }
                else:
                    return {
                        "success": False,
                        "message": "RUC no encontrado"
                    }
            else:
                raise HTTPException(status_code=response.status_code, detail="Error en API externa")
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="Timeout consultando RUC")
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

@app.get("/c/{short_code}")
async def redirect_short_link(short_code: str):
    """Redireccionar enlaces cortos locales"""
    
    try:
        # Buscar el enlace corto en la base de datos local
        if short_code in short_links_db:
            long_url = short_links_db[short_code]
            return RedirectResponse(url=long_url, status_code=302)
        else:
            raise HTTPException(status_code=404, detail="Enlace corto no encontrado")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando redirección: {str(e)}")

# Endpoint para validación documental con Gemini
@app.post("/api/v1/validate-document")
async def validate_document(
    file: UploadFile = File(...),
    firstName: str = Form(...),
    lastName: str = Form(...),
    validationType: str = Form(...),
    academicType: Optional[str] = Form(None)
):
    """Validar documento usando Gemini AI"""
    try:
        # Validar tipo de archivo
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")
        
        # Validar tamaño (máximo 5MB)
        file_content = await file.read()
        if len(file_content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="El archivo es demasiado grande")
        
        # Simular validación con Gemini (aquí iría la integración real)
        # Por ahora, implementamos una validación simulada
        validation_result = await simulate_gemini_validation(
            file_content, 
            firstName, 
            lastName, 
            validationType, 
            academicType
        )
        
        return validation_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en validación: {str(e)}")

async def simulate_gemini_validation(
    file_content: bytes,
    first_name: str,
    last_name: str,
    validation_type: str,
    academic_type: Optional[str] = None
) -> Dict[str, Any]:
    """Simular validación con Gemini AI"""
    
    # Simular procesamiento del documento
    import time
    import random
    
    # Simular tiempo de procesamiento
    await asyncio.sleep(2)
    
    # Simular resultado de validación (85% de éxito)
    is_valid = random.random() > 0.15
    
    if is_valid:
        if validation_type == 'academic':
            if academic_type == 'teacher':
                message = f"Documento de docente validado para {first_name} {last_name}"
            else:
                message = f"Documento de estudiante validado para {first_name} {last_name}"
        else:
            message = f"Documento SME validado para {first_name} {last_name}"
            
        return {
            "valid": True,
            "message": message,
            "confidence": round(random.uniform(0.85, 0.98), 2)
        }
    else:
        reasons = [
            "El documento no es legible",
            "El nombre en el documento no coincide",
            "El documento no corresponde al tipo solicitado",
            "La calidad de la imagen es insuficiente"
        ]
        
        return {
            "valid": False,
            "reason": random.choice(reasons),
            "confidence": round(random.uniform(0.60, 0.84), 2)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)