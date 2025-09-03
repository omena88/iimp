from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import urllib.parse
import string
import random

app = FastAPI(
    title="IIMP Checkout API",
    description="API para el sistema de checkout de IIMP",
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

# Servir archivos estáticos
app.mount("/assets", StaticFiles(directory="../frontend/assets"), name="assets")
app.mount("/js", StaticFiles(directory="../frontend/js"), name="js")
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

# Base de datos en memoria para órdenes
orders_db = {}

@app.get("/")
async def read_root():
    return {"message": "IIMP Checkout API"}

@app.post("/api/v1/create-order-link")
async def create_order_link(request: dict):
    """
    Genera un shortlink personalizado para el checkout
    """
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
        base_url = "http://localhost:8000"
        long_url = f"{base_url}/checkout.html?{query_string}"
        
        # Generar shortlink simple
        short_code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        short_url = f"{base_url}/c/{short_code}"
        
        return {
            "long_url": long_url,
            "short_url": short_url,
            "order_id": order_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando link: {str(e)}")

@app.post("/api/v1/consultar-ruc")
async def consultar_ruc(request: dict):
    """
    Consulta información de RUC
    """
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
    """
    Verifica inscripciones existentes
    """
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