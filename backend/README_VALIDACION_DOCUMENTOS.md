# Sistema de Validación de Documentos con IA

Este sistema implementa validación avanzada de documentos usando Gemini AI para analizar el contenido de documentos SME (Pequeña y Mediana Empresa) y académicos (estudiantes y docentes).

## Configuración

### 1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar API Key de Gemini AI

1. Obtén tu API key en: https://makersuite.google.com/app/apikey
2. Copia el archivo `.env.example` como `.env`:
   ```bash
   copy .env.example .env
   ```
3. Edita el archivo `.env` y reemplaza `your_gemini_api_key_here` con tu API key real:
   ```
   GEMINI_API_KEY=tu_api_key_aqui
   ```

### 3. Iniciar el Servidor

```bash
python simple_server.py
```

El servidor estará disponible en: http://localhost:8000

## Endpoints de Validación

### 1. Validación General
**POST** `/api/v1/validate-document`

**Parámetros (multipart/form-data):**
- `validationType`: "sme" o "academic"
- `firstName`: Nombre del solicitante
- `lastName`: Apellido del solicitante
- `docType`: Tipo de documento de identidad
- `docNumber`: Número de documento de identidad
- `document`: Archivo del documento (PDF, JPG, PNG)

### 2. Validación SME Específica
**POST** `/api/v1/validate-sme-document`

**Parámetros (multipart/form-data):**
- `firstName`: Nombre del titular
- `lastName`: Apellido del titular
- `docType`: Tipo de documento
- `docNumber`: Número de documento
- `document`: Archivo del documento empresarial

### 3. Validación Académica Específica
**POST** `/api/v1/validate-academic-document`

**Parámetros (multipart/form-data):**
- `firstName`: Nombre del estudiante/docente
- `lastName`: Apellido del estudiante/docente
- `docType`: "student" o "teacher"/"docente"
- `docNumber`: Número de documento
- `document`: Archivo del documento académico

## Criterios de Validación

### Documentos SME
- Documento oficial de registro empresarial
- Información de la empresa (RUC, razón social)
- Clasificación de tamaño (micro, pequeña, mediana)
- Vigencia del documento
- Correspondencia con datos del titular

### Documentos Académicos

#### Estudiantes
- Documento oficial de institución educativa
- Nombre completo del estudiante
- Programa de estudios o carrera
- Institución donde estudia
- Certificación de condición estudiantil

#### Docentes
- Documento oficial de institución educativa
- Nombre completo del docente
- Materia o área de enseñanza
- Institución donde labora
- Certificación de condición docente

## Respuesta de la API

```json
{
  "valid": true/false,
  "reason": "Explicación del resultado",
  "details": {
    "file_type_valid": true/false,
    "content_analysis": {
      "valid": true/false,
      "confidence": 0.0-1.0,
      "criteria_met": {
        "official_document": true/false,
        "name_matches": true/false,
        "institution_info": true/false,
        "academic_status": true/false,
        "document_current": true/false
      },
      "extracted_info": {
        "student_name": "nombre extraído",
        "institution": "institución",
        "program": "programa/materia",
        "status": "estado académico"
      }
    },
    "ai_confidence": 0.0-1.0,
    "validation_type": "Academic - Student/Teacher"
  }
}
```

## Modo de Funcionamiento

### Con Gemini AI Configurado
- Análisis inteligente del contenido del documento
- Extracción de texto de PDFs
- Procesamiento de imágenes
- Validación basada en criterios específicos
- Confianza y detalles del análisis

### Sin Gemini AI (Modo Básico)
- Validación de tipo de archivo
- Verificación de presencia de campos requeridos
- Respuesta básica sin análisis de contenido
- Mensaje indicando que se requiere configuración de IA

## Archivos Soportados

- **PDF**: Extracción de texto automática
- **JPG/JPEG**: Procesamiento de imagen para IA
- **PNG**: Procesamiento de imagen para IA

**Tamaño máximo**: 10MB por archivo

## Seguridad

- Las API keys se manejan mediante variables de entorno
- Los archivos se procesan en memoria sin almacenamiento permanente
- Validación de tipos de archivo antes del procesamiento
- Manejo de errores robusto

## Troubleshooting

### Error: "Gemini AI no configurado"
- Verifica que la variable `GEMINI_API_KEY` esté configurada
- Asegúrate de que la API key sea válida
- Reinicia el servidor después de configurar la variable

### Error: "Tipo de archivo no válido"
- Solo se permiten archivos PDF, JPG, JPEG y PNG
- Verifica que el archivo no esté corrupto
- Asegúrate de que el tamaño no exceda 10MB

### Error de instalación de dependencias
- Actualiza pip: `python -m pip install --upgrade pip`
- Instala las dependencias una por una si hay conflictos
- Verifica la versión de Python (recomendado 3.8+)