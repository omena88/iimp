# API Testing Guide - IIMP Checkout System

## Endpoints Disponibles

### 1. Crear Link de Checkout
**Endpoint:** `POST /api/v1/create-order-link`

**Descripción:** Genera un shortlink personalizado para el checkout con información pre-poblada.

**Request Body:**
```json
{
  "participant_name": "Juan Pérez",
  "participant_email": "juan.perez@email.com",
  "document_type": "DNI",
  "document_number": "12345678",
  "phone": "+51987654321",
  "company": "Empresa ABC",
  "ruc": "20123456789",
  "inscription_type": "convencionista",
  "product_id": "conv_nacional",
  "quantity": 1,
  "language": "es"
}
```

**Response:**
```json
{
  "long_url": "http://localhost:8000/checkout.html?name=Juan+P%C3%A9rez&email=juan.perez%40email.com&...",
  "short_url": "http://localhost:8000/c/abc123",
  "order_id": "order_12345"
}
```

### 2. Consultar RUC
**Endpoint:** `POST /api/v1/consultar-ruc`

**Descripción:** Consulta información de una empresa por RUC.

**Request Body:**
```json
{
  "ruc": "20123456789"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "ruc": "20123456789",
    "razon_social": "EMPRESA EJEMPLO S.A.C.",
    "estado": "ACTIVO",
    "direccion": "AV. EJEMPLO 123"
  }
}
```

### 3. Verificar Inscripciones Existentes
**Endpoint:** `POST /api/v1/check-inscriptions`

**Descripción:** Verifica si una persona ya está inscrita en el evento.

**Request Body:**
```json
{
  "document_type": "DNI",
  "document_number": "12345678",
  "email": "juan.perez@email.com"
}
```

**Response:**
```json
{
  "exists": false,
  "message": "No se encontraron inscripciones previas",
  "inscriptions": []
}
```

## Cómo Probar los Endpoints

### Opción 1: Usando curl

```bash
# 1. Crear link de checkout
curl -X POST "http://localhost:8000/api/v1/create-order-link" \
  -H "Content-Type: application/json" \
  -d '{
    "participant_name": "Juan Pérez",
    "participant_email": "juan.perez@email.com",
    "document_type": "DNI",
    "document_number": "12345678",
    "phone": "+51987654321",
    "company": "Empresa ABC",
    "ruc": "20123456789",
    "inscription_type": "convencionista",
    "product_id": "conv_nacional",
    "quantity": 1,
    "language": "es"
  }'

# 2. Consultar RUC
curl -X POST "http://localhost:8000/api/v1/consultar-ruc" \
  -H "Content-Type: application/json" \
  -d '{"ruc": "20123456789"}'

# 3. Verificar inscripciones
curl -X POST "http://localhost:8000/api/v1/check-inscriptions" \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "DNI",
    "document_number": "12345678",
    "email": "juan.perez@email.com"
  }'
```

### Opción 2: Usando PowerShell

```powershell
# 1. Crear link de checkout
$body = @{
    participant_name = "Juan Pérez"
    participant_email = "juan.perez@email.com"
    document_type = "DNI"
    document_number = "12345678"
    phone = "+51987654321"
    company = "Empresa ABC"
    ruc = "20123456789"
    inscription_type = "convencionista"
    product_id = "conv_nacional"
    quantity = 1
    language = "es"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/create-order-link" -Method POST -Body $body -ContentType "application/json"

# 2. Consultar RUC
$rucBody = @{ ruc = "20123456789" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/consultar-ruc" -Method POST -Body $rucBody -ContentType "application/json"

# 3. Verificar inscripciones
$checkBody = @{
    document_type = "DNI"
    document_number = "12345678"
    email = "juan.perez@email.com"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/check-inscriptions" -Method POST -Body $checkBody -ContentType "application/json"
```

### Opción 3: Usando Postman

1. Abrir Postman
2. Crear una nueva request POST
3. URL: `http://localhost:8000/api/v1/create-order-link`
4. Headers: `Content-Type: application/json`
5. Body: Seleccionar "raw" y "JSON", luego pegar el JSON del request body
6. Enviar la request

## Notas Importantes

- Asegúrate de que el servidor esté corriendo en `http://localhost:8000`
- Los endpoints devuelven respuestas en formato JSON
- El shortlink generado redirige al checkout con los datos pre-poblados
- Los parámetros de URL están codificados correctamente para caracteres especiales

## Estructura de Respuesta de Errores

```json
{
  "detail": "Descripción del error"
}
```

## Códigos de Estado HTTP

- `200`: Éxito
- `400`: Error en los datos enviados
- `404`: Recurso no encontrado
- `500`: Error interno del servidor