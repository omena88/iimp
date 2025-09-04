#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API de Validación de Documentos IIMP
Replica la lógica del archivo PHP con mejoras en Python
"""

import os
import json
import base64
import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
from dotenv import load_dotenv
from config import config

# Cargar variables de entorno
load_dotenv()

# Configurar logging
log_level = logging.DEBUG if not config.is_production else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

# Configuración
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyA3JkxvemqX-n-igyWwETAhEqLYuBJFtUk')
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'

# Crear aplicación FastAPI
app = FastAPI(
    title="IIMP Document Validation API",
    description="API para validación de documentos SME y académicos",
    version="1.0.1"
)

# Configurar CORS con orígenes dinámicos
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DocumentValidator:
    """Clase para validación de documentos usando Gemini AI"""
    
    def __init__(self):
        self.gemini_api_key = GEMINI_API_KEY
        self.gemini_url = GEMINI_URL
        self.allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf']
        self.max_file_size = 10 * 1024 * 1024  # 10MB
    
    def validate_file_type(self, file: UploadFile) -> bool:
        """Valida el tipo de archivo"""
        return file.content_type in self.allowed_types
    
    def validate_file_size(self, file_content: bytes) -> bool:
        """Valida el tamaño del archivo"""
        return len(file_content) <= self.max_file_size
    
    def clean_gemini_response(self, response: str) -> str:
        """Limpia la respuesta de Gemini removiendo markdown"""
        clean_response = response.strip()
        
        # Remover triple backticks y etiquetas de markdown
        clean_response = re.sub(r'^```json\s*', '', clean_response)
        clean_response = re.sub(r'\s*```$', '', clean_response)
        clean_response = re.sub(r'^```\s*', '', clean_response)
        clean_response = re.sub(r'\s*```$', '', clean_response)
        
        # Remover etiquetas de markdown adicionales
        clean_response = re.sub(r'^`json\s*', '', clean_response)
        clean_response = re.sub(r'\s*`$', '', clean_response)
        
        # Si la respuesta aún contiene markdown, intentar extraer solo el JSON
        if '```' in clean_response or '`' in clean_response:
            match = re.search(r'\{.*\}', clean_response, re.DOTALL)
            if match:
                clean_response = match.group(0)
        
        return clean_response.strip()
    
    def call_gemini_api(self, prompt: str, file_content: bytes, mime_type: str) -> Dict[str, Any]:
        """Llama a la API de Gemini para validación"""
        try:
            # Codificar archivo en base64
            base64_data = base64.b64encode(file_content).decode('utf-8')
            
            # Preparar request body
            request_body = {
                'contents': [{
                    'parts': [
                        {'text': prompt},
                        {
                            'inline_data': {
                                'mime_type': mime_type,
                                'data': base64_data
                            }
                        }
                    ]
                }],
                'generationConfig': {
                    'temperature': 0.1,
                    'topK': 1,
                    'topP': 1,
                    'maxOutputTokens': 1024
                }
            }
            
            # Hacer request a Gemini
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                f"{self.gemini_url}?key={self.gemini_api_key}",
                headers=headers,
                json=request_body,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Error en respuesta de Gemini: {response.status_code} - {response.text}")
                return {
                    'valid': False,
                    'reason': 'Error en el servicio de validación',
                    'confidence': 0,
                    'error_code': response.status_code
                }
            
            data = response.json()
            
            if not data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text'):
                logger.error("Respuesta inválida de Gemini")
                return {
                    'valid': False,
                    'reason': 'Respuesta inválida del servicio de validación',
                    'confidence': 0
                }
            
            gemini_response = data['candidates'][0]['content']['parts'][0]['text']
            logger.info(f"Respuesta raw de Gemini: {gemini_response}")
            
            # Limpiar respuesta
            clean_response = self.clean_gemini_response(gemini_response)
            logger.info(f"Respuesta limpia de Gemini: {clean_response}")
            
            # Parsear JSON
            try:
                validation_result = json.loads(clean_response)
            except json.JSONDecodeError as e:
                logger.error(f"Error parseando JSON: {e}")
                # Intentar extraer JSON si está dentro de markdown
                match = re.search(r'\{.*\}', gemini_response, re.DOTALL)
                if match:
                    extracted_json = match.group(0)
                    try:
                        validation_result = json.loads(extracted_json)
                    except json.JSONDecodeError:
                        return {
                            'valid': False,
                            'reason': f'Error en el procesamiento de la validación: {str(e)}. Respuesta de IA: {gemini_response[:200]}',
                            'confidence': 0,
                            'raw_response': gemini_response
                        }
                else:
                    return {
                        'valid': False,
                        'reason': f'Error en el procesamiento de la validación: No se encontró JSON válido. Respuesta de IA: {gemini_response[:200]}',
                        'confidence': 0,
                        'raw_response': gemini_response
                    }
            
            # Validar estructura de respuesta
            if 'valid' not in validation_result:
                logger.error(f"Respuesta de Gemini no tiene campo 'valid': {validation_result}")
                return {
                    'valid': False,
                    'reason': f'Respuesta de IA incompleta - falta campo de validación. Respuesta recibida: {clean_response[:200]}',
                    'confidence': 0,
                    'raw_response': gemini_response
                }
            
            logger.info(f"JSON parseado exitosamente: {validation_result}")
            return validation_result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión con Gemini: {e}")
            return {
                'valid': False,
                'reason': 'Error de conexión con el servicio de validación',
                'confidence': 0,
                'connection_error': str(e)
            }
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return {
                'valid': False,
                'reason': f'Error inesperado en la validación: {str(e)}',
                'confidence': 0
            }
    
    def validate_sme_document(self, file_content: bytes, user_name: str, user_lastname: str, mime_type: str) -> Dict[str, Any]:
        """Valida documento SME usando Gemini AI"""
        prompt = f"""Analiza este documento PDF o imagen y verifica si es un certificado válido de membresía SME (Sociedad Minera, Metalúrgica y de Explotación). 
    
CRITERIOS DE VALIDACIÓN ESTRICTOS:
1. El documento DEBE ser un certificado oficial de SME (Sociedad Minera, Metalúrgica y de Explotación)
2. DEBE contener el nombre completo del miembro que coincida con los datos proporcionados
3. DEBE estar vigente (no expirado)
4. DEBE ser legible y auténtico (no una copia falsificada)
5. DEBE ser un documento oficial, no una captura de pantalla o imagen informal

DATOS DEL USUARIO A VERIFICAR:
- Nombre: {user_name}
- Apellido: {user_lastname}

ANÁLISIS REQUERIDO:
- Identifica el tipo de documento (certificado, carnet, credencial, etc.)
- Extrae el nombre completo que aparece en el documento
- Verifica si es un documento oficial de SME
- Comprueba si está vigente
- Evalúa la legibilidad y autenticidad

Responde ÚNICAMENTE con un JSON válido (sin markdown, sin backticks, sin formato adicional):
{{
    "valid": true/false,
    "reason": "explicación detallada de por qué es válido o inválido",
    "confidence": 0-100,
    "document_type": "tipo de documento identificado",
    "member_name": "nombre completo encontrado en el documento",
    "analysis": {{
        "is_official_sme": true/false,
        "name_matches": true/false,
        "is_current": true/false,
        "is_legible": true/false,
        "is_authentic": true/false
    }}
}}

IMPORTANTE: 
- NO uses markdown, NO uses backticks, NO uses formato adicional
- Responde SOLO el JSON puro
- Si el documento no es un certificado oficial de SME, marca como inválido independientemente de otros factores."""
        
        return self.call_gemini_api(prompt, file_content, mime_type)
    
    def validate_academic_document(self, file_content: bytes, user_name: str, user_lastname: str, academic_type: str, mime_type: str) -> Dict[str, Any]:
        """Valida documento académico usando Gemini AI"""
        # Mapear tipos de inglés a español
        if academic_type == 'teacher':
            academic_title = 'docente'
        elif academic_type == 'student':
            academic_title = 'estudiante'
        else:
            # Mantener compatibilidad con valores en español
            academic_title = 'docente' if academic_type == 'docente' else 'estudiante'
        
        academic_entity = 'universidad o institución educativa'
        
        prompt = f"""Analiza este documento PDF o imagen y verifica si es un documento válido que certifique que la persona es {academic_title} de una {academic_entity}.

CRITERIOS DE VALIDACIÓN ESTRICTOS:
1. El documento DEBE ser un carnet universitario, credencial de docente, carta de la universidad, o documento oficial que certifique la condición de {academic_title}
2. DEBE contener el nombre completo del {academic_title} que coincida con los datos proporcionados
3. DEBE estar vigente (no expirado)
4. DEBE ser legible y auténtico (no una copia falsificada)
5. DEBE ser un documento oficial de una institución educativa reconocida
6. DEBE especificar claramente que la persona es {academic_title}

DATOS DEL USUARIO A VERIFICAR:
- Nombre: {user_name}
- Apellido: {user_lastname}
- Tipo: {academic_title}

ANÁLISIS REQUERIDO:
- Identifica el tipo de documento (carnet, credencial, carta, etc.)
- Extrae el nombre completo que aparece en el documento
- Verifica si es un documento oficial de una institución educativa
- Comprueba si está vigente
- Evalúa la legibilidad y autenticidad
- Confirma que especifica la condición de {academic_title}

Responde ÚNICAMENTE con un JSON válido (sin markdown, sin backticks, sin formato adicional):
{{
    "valid": true/false,
    "reason": "explicación detallada de por qué es válido o inválido",
    "confidence": 0-100,
    "document_type": "tipo de documento identificado",
    "member_name": "nombre completo encontrado en el documento",
    "institution": "nombre de la institución educativa",
    "analysis": {{
        "is_official_document": true/false,
        "name_matches": true/false,
        "is_current": true/false,
        "is_legible": true/false,
        "is_authentic": true/false,
        "specifies_academic_status": true/false
    }}
}}

IMPORTANTE: 
- NO uses markdown, NO uses backticks, NO uses formato adicional
- Responde SOLO el JSON puro
- Si el documento no especifica claramente que la persona es {academic_title}, marca como inválido
- Si el documento no es de una institución educativa reconocida, marca como inválido"""
        
        return self.call_gemini_api(prompt, file_content, mime_type)

# Instanciar validador
validator = DocumentValidator()

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "IIMP Document Validation API",
        "version": "1.0.1",
        "status": "active",
        "endpoints": [
            "/api/v1/validate-sme-document",
            "/api/v1/validate-academic-document",
            "/api/v1/validate-document"
        ]
    }

@app.post("/api/v1/validate-sme-document")
async def validate_sme_document(
    document: UploadFile = File(...),
    user_name: str = Form(...),
    user_lastname: str = Form(...)
):
    """Endpoint para validar documento SME"""
    try:
        logger.info(f"validate-sme-document - Petición recibida para {user_name} {user_lastname}")
        
        # Validar tipo de archivo
        if not validator.validate_file_type(document):
            raise HTTPException(
                status_code=400,
                detail="Tipo de archivo no permitido. Solo se permiten PDF, JPG y PNG"
            )
        
        # Leer archivo
        file_content = await document.read()
        logger.info(f"Archivo leído: {len(file_content)} bytes")
        
        # Validar tamaño
        if not validator.validate_file_size(file_content):
            raise HTTPException(
                status_code=400,
                detail="El archivo es demasiado grande. Máximo 10MB"
            )
        
        # Validar con Gemini
        logger.info("Iniciando validación SME con Gemini...")
        validation_result = validator.validate_sme_document(
            file_content, user_name, user_lastname, document.content_type
        )
        
        logger.info(f"Resultado de validación SME: {validation_result}")
        
        # Agregar análisis detallado si está disponible
        if 'analysis' in validation_result:
            analysis = validation_result['analysis']
            details = []
            
            if 'is_official_sme' in analysis:
                details.append(('✓' if analysis['is_official_sme'] else '✗') + ' Documento oficial de SME')
            if 'name_matches' in analysis:
                details.append(('✓' if analysis['name_matches'] else '✗') + ' Nombre coincide')
            if 'is_current' in analysis:
                details.append(('✓' if analysis['is_current'] else '✗') + ' Documento vigente')
            if 'is_legible' in analysis:
                details.append(('✓' if analysis['is_legible'] else '✗') + ' Documento legible')
            if 'is_authentic' in analysis:
                details.append(('✓' if analysis['is_authentic'] else '✗') + ' Documento auténtico')
            
            if details:
                validation_result['reason'] += "\n\nAnálisis detallado:\n" + "\n".join(details)
        
        return JSONResponse(content=validation_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en validación SME: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.post("/api/v1/validate-academic-document")
async def validate_academic_document(
    document: UploadFile = File(...),
    user_name: str = Form(...),
    user_lastname: str = Form(...),
    academic_type: str = Form(...)
):
    """Endpoint para validar documento académico"""
    try:
        logger.info(f"validate-academic-document - Petición recibida para {user_name} {user_lastname} ({academic_type})")
        
        # Validar tipo de archivo
        if not validator.validate_file_type(document):
            raise HTTPException(
                status_code=400,
                detail="Tipo de archivo no permitido. Solo se permiten PDF, JPG y PNG"
            )
        
        # Leer archivo
        file_content = await document.read()
        logger.info(f"Archivo leído: {len(file_content)} bytes")
        
        # Validar tamaño
        if not validator.validate_file_size(file_content):
            raise HTTPException(
                status_code=400,
                detail="El archivo es demasiado grande. Máximo 10MB"
            )
        
        # Validar con Gemini
        logger.info("Iniciando validación académica con Gemini...")
        validation_result = validator.validate_academic_document(
            file_content, user_name, user_lastname, academic_type, document.content_type
        )
        
        logger.info(f"Resultado de validación académica: {validation_result}")
        
        return JSONResponse(content=validation_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en validación académica: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.post("/api/v1/validate-document")
async def validate_document(
    document: UploadFile = File(...),
    validationType: str = Form(...),
    firstName: str = Form(...),
    lastName: str = Form(...),
    docType: Optional[str] = Form(None),
    docNumber: Optional[str] = Form(None)
):
    """Endpoint general para validar documentos"""
    try:
        logger.info(f"validate-document - Petición recibida: {validationType} para {firstName} {lastName}")
        
        if validationType == 'sme':
            return await validate_sme_document(document, firstName, lastName)
        elif validationType == 'academic':
            academic_type = docType if docType in ['docente', 'estudiante'] else 'estudiante'
            return await validate_academic_document(document, firstName, lastName, academic_type)
        else:
            raise HTTPException(
                status_code=400,
                detail="Tipo de validación no válido. Use 'sme' o 'academic'"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en validación general: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.get("/config")
async def get_config():
    """Endpoint para obtener configuración del frontend"""
    return config.get_frontend_config()

if __name__ == "__main__":
    import uvicorn
    
    # Usar configuración dinámica
    server_config = config.server_config
    
    logger.info(f"Iniciando servidor en modo {config.environment}")
    logger.info(f"URL base de API: {config.api_base_url}")
    
    uvicorn.run(
        "validation_api:app",
        **server_config
    )