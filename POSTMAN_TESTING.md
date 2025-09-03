# Guía de Pruebas con Postman - IIMP API

## 🚀 URL Base del API Desplegado
```
https://apis-iimp-web.di8b44.easypanel.host
```

## 📋 Endpoints Disponibles

### 1. Verificar Estado del API
**GET** `/api/`
- **URL Completa**: `https://apis-iimp-web.di8b44.easypanel.host/api/`
- **Método**: GET
- **Headers**: No requeridos
- **Respuesta esperada**:
```json
{
  "message": "Sistema de Procesamiento de Órdenes API"
}
```

### 2. Generar Shortlink de Checkout
**POST** `/api/v1/generate-shortlink`
- **URL Completa**: `https://apis-iimp-web.di8b44.easypanel.host/api/v1/generate-shortlink`
- **Método**: POST
- **Headers**:
  ```
  Content-Type: application/json
  ```
- **Body (JSON)**:
```json
{
  "product_id": 154,
  "product_name": "Curso PERUMIN 37",
  "price": 500.00,
  "currency": "USD",
  "customer_data": {
    "name": "Juan Pérez",
    "email": "juan@example.com",
    "phone": "+51987654321"
  },
  "training_days": ["2024-09-23", "2024-09-24"],
  "language": "es"
}
```

### 3. Consultar RUC
**POST** `/api/v1/consultar-ruc`
- **URL Completa**: `https://apis-iimp-web.di8b44.easypanel.host/api/v1/consultar-ruc`
- **Método**: POST
- **Headers**:
  ```
  Content-Type: application/json
  ```
- **Body (JSON)**:
```json
{
  "ruc": "20123456789"
}
```

### 4. Verificar Inscripciones
**POST** `/api/v1/check-inscriptions`
- **URL Completa**: `https://apis-iimp-web.di8b44.easypanel.host/api/v1/check-inscriptions`
- **Método**: POST
- **Headers**:
  ```
  Content-Type: application/json
  ```
- **Body (JSON)**:
```json
{
  "email": "juan@example.com",
  "product_id": 154
}
```

## 🔧 Configuración en Postman

### Paso 1: Crear Nueva Colección
1. Abrir Postman
2. Crear nueva colección llamada "IIMP API Tests"
3. Agregar variable de entorno:
   - Variable: `base_url`
   - Valor: `https://apis-iimp-web.di8b44.easypanel.host`

### Paso 2: Configurar Requests

#### Request 1: Estado del API
- **Nombre**: "Check API Status"
- **Método**: GET
- **URL**: `{{base_url}}/api/`

#### Request 2: Generar Shortlink
- **Nombre**: "Generate Shortlink"
- **Método**: POST
- **URL**: `{{base_url}}/api/v1/generate-shortlink`
- **Headers**: `Content-Type: application/json`
- **Body**: Raw JSON (copiar el ejemplo de arriba)

#### Request 3: Consultar RUC
- **Nombre**: "Consultar RUC"
- **Método**: POST
- **URL**: `{{base_url}}/api/v1/consultar-ruc`
- **Headers**: `Content-Type: application/json`
- **Body**: Raw JSON (copiar el ejemplo de arriba)

#### Request 4: Verificar Inscripciones
- **Nombre**: "Check Inscriptions"
- **Método**: POST
- **URL**: `{{base_url}}/api/v1/check-inscriptions`
- **Headers**: `Content-Type: application/json`
- **Body**: Raw JSON (copiar el ejemplo de arriba)

## 📖 Documentación Swagger

Puedes acceder a la documentación interactiva en:
```
https://apis-iimp-web.di8b44.easypanel.host/api/docs
```

Esta documentación te permitirá:
- Ver todos los endpoints disponibles
- Probar directamente desde el navegador
- Ver los esquemas de datos requeridos
- Obtener ejemplos de respuestas

## 🧪 Ejemplos de Pruebas

### Prueba Básica con cURL
```bash
# Verificar estado del API
curl -X GET "https://apis-iimp-web.di8b44.easypanel.host/api/"

# Generar shortlink
curl -X POST "https://apis-iimp-web.di8b44.easypanel.host/api/v1/generate-shortlink" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 154,
    "product_name": "Curso PERUMIN 37",
    "price": 500.00,
    "currency": "USD",
    "customer_data": {
      "name": "Juan Pérez",
      "email": "juan@example.com",
      "phone": "+51987654321"
    },
    "training_days": ["2024-09-23", "2024-09-24"],
    "language": "es"
  }'
```

## 🔍 Solución de Problemas

### Error 404 "Not Found"
- Verificar que la URL esté correcta
- Asegurarse de incluir `/api/` en la ruta
- Revisar que el método HTTP sea correcto

### Error 422 "Validation Error"
- Verificar que el JSON esté bien formateado
- Comprobar que todos los campos requeridos estén presentes
- Revisar los tipos de datos (números, strings, arrays)

### Error 500 "Internal Server Error"
- Verificar que el servidor esté funcionando
- Revisar los logs del servidor
- Contactar al administrador del sistema

## 📞 Soporte

Para más información o soporte técnico, revisar:
- Documentación Swagger: `/api/docs`
- Logs del servidor en EasyPanel
- Repositorio del proyecto en GitHub