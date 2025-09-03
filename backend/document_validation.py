import os
import base64
import io
from typing import Dict, Any, Optional, Tuple
from PIL import Image
import PyPDF2
import google.generativeai as genai
from fastapi import UploadFile, HTTPException

# Configurar Gemini AI
# Obtener API key de variable de entorno
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY_HERE')
if GEMINI_API_KEY == 'YOUR_GEMINI_API_KEY_HERE':
    print("ADVERTENCIA: No se ha configurado GEMINI_API_KEY. Las validaciones con IA no funcionarán.")
    print("Por favor, configura la variable de entorno GEMINI_API_KEY con tu API key de Google Gemini.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

class DocumentValidator:
    def __init__(self):
        if GEMINI_API_KEY != 'YOUR_GEMINI_API_KEY_HERE':
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
        
    def validate_file_type(self, file: UploadFile) -> bool:
        """Valida que el archivo sea PDF, JPG o PNG"""
        allowed_types = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']
        return file.content_type in allowed_types
    
    def extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extrae texto de un archivo PDF"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error al procesar PDF: {str(e)}")
    
    def process_image(self, file_content: bytes) -> str:
        """Procesa una imagen y la convierte a base64 para Gemini"""
        try:
            image = Image.open(io.BytesIO(file_content))
            # Convertir a RGB si es necesario
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Redimensionar si es muy grande (máximo 1024x1024)
            max_size = (1024, 1024)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convertir a base64
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            return img_base64
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error al procesar imagen: {str(e)}")
    
    async def validate_sme_document(self, file: UploadFile, first_name: str, last_name: str) -> Dict[str, Any]:
        """Valida documento SME usando IA con criterios estrictos"""
        if not self.validate_file_type(file):
            return {
                "valid": False,
                "reason": "Tipo de archivo no válido. Solo se permiten PDF, JPG y PNG.",
                "confidence": 0
            }
        
        # Verificar si Gemini AI está configurado
        if GEMINI_API_KEY == 'YOUR_GEMINI_API_KEY_HERE':
            return {
                "valid": False,
                "reason": "Servicio de validación no disponible. Configure GEMINI_API_KEY.",
                "confidence": 0
            }
        
        try:
            file_content = await file.read()
            
            # Prompt estricto basado en la versión PHP estable
            prompt = f"""Analiza este documento PDF o imagen y verifica si es un certificado válido de membresía SME (Sociedad Minera, Metalúrgica y de Explotación). 
    
CRITERIOS DE VALIDACIÓN ESTRICTOS:
1. El documento DEBE ser un certificado oficial de SME (Sociedad Minera, Metalúrgica y de Explotación)
2. DEBE contener el nombre completo del miembro que coincida con los datos proporcionados
3. DEBE estar vigente (no expirado)
4. DEBE ser legible y auténtico (no una copia falsificada)
5. DEBE ser un documento oficial, no una captura de pantalla o imagen informal

DATOS DEL USUARIO A VERIFICAR:
- Nombre: {first_name}
- Apellido: {last_name}

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
            
            # Configurar generación con parámetros estrictos
            generation_config = {
                'temperature': 0.1,
                'top_k': 1,
                'top_p': 1,
                'max_output_tokens': 1024
            }
            
            if file.content_type == 'application/pdf':
                # Procesar PDF
                text_content = self.extract_text_from_pdf(file_content)
                response = self.model.generate_content(
                    [prompt, f"Contenido del documento: {text_content}"],
                    generation_config=generation_config
                )
            else:
                # Procesar imagen
                img_base64 = self.process_image(file_content)
                image_part = {
                    "mime_type": "image/jpeg",
                    "data": img_base64
                }
                response = self.model.generate_content(
                    [prompt, image_part],
                    generation_config=generation_config
                )
            
            # Procesar respuesta de Gemini
            result_text = response.text.strip()
            
            # Intentar parsear JSON de la respuesta
            try:
                import json
                # Limpiar la respuesta para extraer solo el JSON
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = result_text[start_idx:end_idx]
                    result = json.loads(json_str)
                else:
                    raise ValueError("No se encontró JSON válido en la respuesta")
            except Exception as parse_error:
                # Si no se puede parsear, marcar como inválido por defecto
                return {
                    "valid": False,
                    "reason": f"Error al procesar respuesta de validación: {str(parse_error)}",
                    "confidence": 0,
                    "document_type": "No identificado",
                    "member_name": "No extraído",
                    "analysis": {
                        "is_official_sme": False,
                        "name_matches": False,
                        "is_current": False,
                        "is_legible": False,
                        "is_authentic": False
                    }
                }
            
            # Validar estructura del JSON
            if not isinstance(result, dict) or 'valid' not in result:
                return {
                    "valid": False,
                    "reason": "Respuesta de validación inválida",
                    "confidence": 0
                }
            
            return result
            
        except Exception as e:
            return {
                "valid": False,
                "reason": f"Error en validación SME: {str(e)}",
                "confidence": 0
            }
    
    async def validate_academic_document(self, file: UploadFile, first_name: str, last_name: str, doc_type: str, doc_number: str) -> Dict[str, Any]:
        """
        Valida un documento académico (estudiante o docente) usando Gemini AI con criterios estrictos
        """
        try:
            # Validar tipo de archivo
            if not self.validate_file_type(file):
                return {
                    "valid": False,
                    "reason": "Tipo de archivo no válido. Solo se permiten PDF, JPG, JPEG, PNG",
                    "confidence": 0
                }

            # Determinar tipo de validación
            if doc_type.lower() == "teacher" or doc_type.lower() == "docente":
                academic_type = "docente"
                academic_title = "docente"
                academic_entity = "universidad o institución educativa"
            else:
                academic_type = "estudiante"
                academic_title = "estudiante"
                academic_entity = "universidad o institución educativa"
            
            # Verificar si Gemini AI está configurado
            if GEMINI_API_KEY == 'YOUR_GEMINI_API_KEY_HERE':
                return {
                    "valid": False,
                    "reason": "Servicio de validación no disponible. Configure GEMINI_API_KEY.",
                    "confidence": 0
                }

            # Leer contenido del archivo
            file_content = await file.read()
            
            # Prompt estricto basado en la versión PHP estable
            prompt = f"""Analiza este documento PDF o imagen y verifica si es un documento válido que certifique que la persona es {academic_title} de una {academic_entity}.
    
CRITERIOS DE VALIDACIÓN ESTRICTOS:
1. El documento DEBE ser un carnet universitario, credencial de docente, carta de la universidad, o documento oficial que certifique la condición de {academic_title}
2. DEBE contener el nombre completo del {academic_title} que coincida con los datos proporcionados
3. DEBE estar vigente (no expirado)
4. DEBE ser legible y auténtico (no una copia falsificada)
5. DEBE ser un documento oficial de una institución educativa reconocida
6. DEBE especificar claramente que la persona es {academic_title}

DATOS DEL USUARIO A VERIFICAR:
- Nombre: {first_name}
- Apellido: {last_name}
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

            # Configurar generación con parámetros estrictos
            generation_config = {
                'temperature': 0.1,
                'top_k': 1,
                'top_p': 1,
                'max_output_tokens': 1024
            }
            
            # Llamar a Gemini AI
            if file.content_type == 'application/pdf':
                # Procesar PDF
                text_content = self.extract_text_from_pdf(file_content)
                response = self.model.generate_content(
                    [prompt, f"Contenido del documento: {text_content}"],
                    generation_config=generation_config
                )
            else:
                # Procesar imagen
                img_base64 = self.process_image(file_content)
                image_part = {
                    "mime_type": "image/jpeg",
                    "data": img_base64
                }
                response = self.model.generate_content(
                    [prompt, image_part],
                    generation_config=generation_config
                )

            # Procesar respuesta
            response_text = response.text.strip()
            
            # Extraer JSON de la respuesta
            import json
            try:
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    result = json.loads(json_str)
                else:
                    raise ValueError("No se encontró JSON válido en la respuesta")
            except Exception as parse_error:
                # Si no se puede parsear, marcar como inválido por defecto
                return {
                    "valid": False,
                    "reason": f"Error al procesar respuesta de validación: {str(parse_error)}",
                    "confidence": 0,
                    "document_type": "No identificado",
                    "member_name": "No extraído",
                    "institution": "No identificada",
                    "analysis": {
                        "is_official_document": False,
                        "name_matches": False,
                        "is_current": False,
                        "is_legible": False,
                        "is_authentic": False,
                        "specifies_academic_status": False
                    }
                }
            
            # Validar estructura del JSON
            if not isinstance(result, dict) or 'valid' not in result:
                return {
                    "valid": False,
                    "reason": "Respuesta de validación inválida",
                    "confidence": 0
                }
            
            return result

        except Exception as e:
            return {
                "valid": False,
                "reason": f"Error durante la validación: {str(e)}",
                "confidence": 0
            }

# Instancia global del validador
document_validator = DocumentValidator()