# IIMP Checkout System

Sistema de checkout para IIMP con API backend y frontend integrado.

## Características

- **Backend API**: FastAPI con endpoints para generar shortlinks de checkout
- **Frontend**: HTML/CSS/JS con formulario de checkout dinámico
- **Integración**: Sistema completo dockerizado para fácil despliegue

## Estructura del Proyecto

```
IIMP-WEB/
├── backend/                 # API FastAPI
│   ├── app/
│   │   ├── core/           # Configuración
│   │   ├── models/         # Modelos de datos
│   │   └── routers/        # Endpoints API
│   ├── main.py             # Aplicación principal
│   └── requirements.txt    # Dependencias Python
├── frontend/               # Frontend web
│   ├── assets/            # Imágenes y recursos
│   ├── css/               # Estilos
│   ├── js/                # JavaScript
│   └── checkout.html      # Página principal
├── Dockerfile             # Configuración Docker
└── docker-compose.yml     # Orquestación de servicios
```

## Despliegue en EasyPanel

### Opción 1: Desde GitHub

1. Conecta tu repositorio GitHub en EasyPanel
2. Selecciona el repositorio: `https://github.com/omena88/iimp.git`
3. EasyPanel detectará automáticamente el Dockerfile
4. Configura el puerto: `80`
5. Despliega la aplicación

### Opción 2: Build Manual

```bash
# Clonar repositorio
git clone https://github.com/omena88/iimp.git
cd iimp

# Build imagen Docker
docker build -t iimp-checkout .

# Ejecutar contenedor
docker run -p 80:80 iimp-checkout
```

## Desarrollo Local

### Con Docker Compose

```bash
# Desarrollo con hot reload
docker-compose --profile dev up iimp-dev

# Producción local
docker-compose up iimp-web
```

### Sin Docker

```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py

# Frontend (servidor separado)
cd frontend
python -m http.server 8080
```

## API Endpoints

- `GET /` - Documentación API (Swagger)
- `POST /generate-shortlink` - Generar shortlink de checkout
- `GET /checkout/{shortlink_id}` - Obtener datos del checkout

## Configuración

### Variables de Entorno

- `ENVIRONMENT`: `development` o `production`
- `DATABASE_URL`: URL de base de datos (opcional)
- `SECRET_KEY`: Clave secreta para JWT (opcional)

### Puertos

- **Producción**: Puerto 80 (HTTP)
- **Desarrollo**: Puerto 8080 (HTTP)
- **API Backend**: Puerto 8000 (interno)

## Tecnologías

- **Backend**: Python 3.11, FastAPI, Uvicorn
- **Frontend**: HTML5, CSS3, JavaScript ES6
- **Servidor Web**: Nginx
- **Orquestación**: Supervisor
- **Containerización**: Docker

## Licencia

Proyecto privado - IIMP