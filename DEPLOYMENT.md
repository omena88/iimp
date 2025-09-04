# Guía de Deployment para Producción

## Configuración de Variables de Entorno

Antes de desplegar en producción, asegúrate de configurar las siguientes variables de entorno:

```bash
# Variable requerida para la API de validación con IA
GEMINI_API_KEY=tu_api_key_de_gemini_aqui

# Variable de entorno (se detecta automáticamente)
ENVIRONMENT=production
```

## Deployment con Docker Compose

### 1. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```bash
GEMINI_API_KEY=tu_api_key_de_gemini_aqui
ENVIRONMENT=production
```

### 2. Construir y ejecutar los servicios

```bash
# Construir las imágenes
docker-compose build

# Ejecutar en producción
docker-compose up -d
```

### 3. Verificar que los servicios estén funcionando

```bash
# Verificar estado de los contenedores
docker-compose ps

# Ver logs del sistema principal
docker-compose logs iimp-web

# Ver logs de la API de validación
docker-compose logs validation-api
```

## Servicios Desplegados

### Servicio Principal (iimp-web)
- **Puerto**: 80
- **Función**: Servidor web frontend + API simple
- **URL**: http://tu-dominio.com

### API de Validación (validation-api)
- **Puerto**: 8001
- **Función**: API de validación de documentos con IA
- **URL**: http://tu-dominio.com:8001
- **Endpoints**:
  - `GET /config` - Configuración de la API
  - `POST /api/v1/validate-sme-document` - Validación SME
  - `POST /api/v1/validate-academic-document` - Validación académica
  - `POST /api/v1/validate-document` - Validación general

## Configuración de URLs Dinámicas

El sistema detecta automáticamente el entorno:

- **Desarrollo**: `localhost` → API en `http://localhost:8001`
- **Producción**: Cualquier otro dominio → API en `https://apis-iimp-web.di8b44.easypanel.host`

### Para cambiar la URL de producción:

1. Edita `frontend/js/validation-config.js`:
```javascript
getApiBaseUrl() {
    if (this.isProduction) {
        return 'https://tu-nuevo-dominio.com:8001'; // Cambiar aquí
    } else {
        return 'http://localhost:8001';
    }
}
```

2. Edita `backend/config.py`:
```python
@property
def api_base_url(self) -> str:
    if self.is_production:
        return "https://tu-nuevo-dominio.com:8001"  # Cambiar aquí
    else:
        return "http://localhost:8001"
```

## Troubleshooting

### Error HTTP 502 en validación

1. **Verificar que la API de validación esté corriendo**:
```bash
curl http://tu-dominio.com:8001/config
```

2. **Verificar logs de la API**:
```bash
docker-compose logs validation-api
```

3. **Verificar variables de entorno**:
```bash
docker-compose exec validation-api env | grep GEMINI
```

### CORS Issues

Si hay problemas de CORS, verifica que el dominio esté incluido en `backend/config.py`:

```python
@property
def cors_origins(self) -> list:
    if self.is_production:
        return [
            "https://tu-dominio.com",
            "https://apis-iimp-web.di8b44.easypanel.host",
            # Agregar más dominios según sea necesario
        ]
```

## Monitoreo

### Logs importantes a monitorear:

```bash
# Logs del sistema principal
docker-compose logs -f iimp-web

# Logs de la API de validación
docker-compose logs -f validation-api

# Logs específicos de nginx
docker-compose exec iimp-web tail -f /var/log/nginx.out.log

# Logs específicos de la validación
docker-compose exec validation-api tail -f /var/log/validation-api.out.log
```

### Health Checks

```bash
# Verificar frontend
curl http://tu-dominio.com

# Verificar API de validación
curl http://tu-dominio.com:8001/config

# Verificar API simple
curl http://tu-dominio.com/api/validate
```

## Actualizaciones

Para actualizar el sistema en producción:

```bash
# 1. Hacer pull de los cambios
git pull origin main

# 2. Reconstruir las imágenes
docker-compose build

# 3. Reiniciar los servicios
docker-compose down
docker-compose up -d

# 4. Verificar que todo funcione
docker-compose ps
docker-compose logs
```