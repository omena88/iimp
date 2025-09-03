import os
import base64
import io
from typing import Dict, Any, Optional, Tuple
from PIL import Image
import PyPDF2
import google.generativeai as genai
from fastapi import UploadFile, HTTPException
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

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
    
    async def validate_sme_document(self, file: UploadFile, first_name: str, last_name: str, doc_type: Optional[str] = None, doc_number: Optional[str] = None) -> Dict[str, Any]:
        """Valida documento SME usando IA con criterios estrictos y parámetros flexibles"""
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
            print(f"Archivo leído: {len(file_content)} bytes")
            
            # Prompt mejorado basado en pruebas exitosas
            prompt = f"""Analiza este documento PDF o imagen y verifica si es un certificado válido de membresía SME (Society for Mining, Metallurgy & Exploration).
    
CRITERIOS DE VALIDACIÓN ESTRICTOS:
1. El documento DEBE ser un certificado oficial, carta de membresía, o credencial de SME (Society for Mining, Metallurgy & Exploration)
2. DEBE contener el nombre completo del miembro que coincida exactamente con: {first_name} {last_name}
3. DEBE estar vigente (verificar fechas de expiración si están presentes)
4. DEBE ser legible y auténtico (evaluar calidad del documento)
5. DEBE ser un documento oficial con membrete, firma, o sellos institucionales
6. DEBE incluir información de membresía como ID de miembro, fechas de vigencia, o tipo de membresía

DATOS DEL USUARIO A VERIFICAR:
- Nombre completo: {first_name} {last_name}

ANÁLISIS REQUERIDO:
- Identifica el tipo específico de documento SME (certificado, carta, credencial, etc.)
- Extrae el nombre completo exacto que aparece en el documento
- Verifica si es un documento oficial de SME con elementos de autenticidad
- Comprueba fechas de vigencia si están disponibles
- Evalúa la calidad, legibilidad y autenticidad del documento
- Confirma que corresponde a membresía activa o certificación SME

Responde ÚNICAMENTE con un JSON válido (sin markdown, sin backticks, sin formato adicional):
{{
    "valid": true/false,
    "reason": "explicación detallada y específica de por qué es válido o inválido",
    "confidence": 0-100,
    "document_type": "tipo específico de documento identificado",
    "member_name": "nombre completo exacto encontrado en el documento",
    "member_id": "ID de miembro si está disponible",
    "expiration_date": "fecha de expiración si está disponible",
    "analysis": {{
        "is_official_sme": true/false,
        "name_matches": true/false,
        "is_current": true/false,
        "is_legible": true/false,
        "is_authentic": true/false,
        "has_official_elements": true/false
    }}
}}

IMPORTANTE: 
- NO uses markdown, NO uses backticks, NO uses formato adicional
- Responde SOLO el JSON puro
- Si el documento no es de SME, marca como inválido
- Sé específico en la razón de validación o rechazo"""
            
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
                print(f"Enviando prompt a Gemini AI...")
                response = self.model.generate_content(
                    [prompt, f"Contenido del documento: {text_content}"],
                    generation_config=generation_config
                )
                print(f"Respuesta de Gemini recibida: {response.text[:200]}...")
            else:
                # Procesar imagen
                img_base64 = self.process_image(file_content)
                image_part = {
                    "mime_type": "image/jpeg",
                    "data": img_base64
                }
                print(f"Enviando prompt a Gemini AI...")
                response = self.model.generate_content(
                    [prompt, image_part],
                    generation_config=generation_config
                )
                print(f"Respuesta de Gemini recibida: {response.text[:200]}...")
            
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
                    },
                    "ai_details": {
                        "prompt_sent": prompt,
                        "raw_response": result_text,
                        "parse_error": str(parse_error)
                    }
                }
            
            # Validar estructura del JSON
            if not isinstance(result, dict) or 'valid' not in result:
                return {
                    "valid": False,
                    "reason": "Respuesta de validación inválida",
                    "confidence": 0,
                    "ai_details": {
                        "prompt_sent": prompt,
                        "raw_response": result_text,
                        "parsed_result": result if isinstance(result, dict) else "No es un diccionario válido"
                    }
                }
            
            # Agregar detalles de IA a la respuesta
            result["ai_details"] = {
                "prompt_sent": prompt,
                "raw_response": result_text,
                "parsed_successfully": True
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
            
            # Prompt mejorado basado en pruebas exitosas
            prompt = f"""Analiza este documento PDF o imagen y verifica si es un documento válido que certifique que la persona es {academic_title} de una institución educativa reconocida.
    
CRITERIOS DE VALIDACIÓN ESTRICTOS:
1. El documento DEBE ser un carnet universitario, credencial de {academic_title}, carta oficial de la universidad, constancia de trabajo, o documento oficial que certifique la condición de {academic_title}
2. DEBE contener el nombre completo que coincida exactamente con: {first_name} {last_name}
3. DEBE estar vigente (verificar fechas si están presentes)
4. DEBE ser legible y auténtico (evaluar calidad del documento)
5. DEBE ser un documento oficial de una institución educativa reconocida con membrete, firma, o sellos
6. DEBE especificar claramente que la persona es {academic_title} (no otro tipo de relación con la institución)
7. DEBE incluir información institucional como nombre de la universidad, facultad, departamento, o cargo específico

DATOS DEL USUARIO A VERIFICAR:
- Nombre completo: {first_name} {last_name}
- Condición esperada: {academic_title}

ANÁLISIS REQUERIDO:
- Identifica el tipo específico de documento académico (carnet, credencial, carta, constancia, etc.)
- Extrae el nombre completo exacto que aparece en el documento
- Verifica si es un documento oficial de una institución educativa reconocida
- Comprueba fechas de vigencia o validez si están disponibles
- Evalúa la calidad, legibilidad y elementos de autenticidad
- Confirma que especifica claramente la condición de {academic_title}
- Identifica la institución educativa y su reconocimiento

Responde ÚNICAMENTE con un JSON válido (sin markdown, sin backticks, sin formato adicional):
{{
    "valid": true/false,
    "reason": "explicación detallada y específica de por qué es válido o inválido",
    "confidence": 0-100,
    "document_type": "tipo específico de documento identificado",
    "member_name": "nombre completo exacto encontrado en el documento",
    "institution": "nombre completo de la institución educativa",
    "academic_position": "cargo o posición académica específica si está disponible",
    "validity_period": "período de validez si está disponible",
    "analysis": {{
        "is_official_document": true/false,
        "name_matches": true/false,
        "is_current": true/false,
        "is_legible": true/false,
        "is_authentic": true/false,
        "specifies_academic_status": true/false,
        "institution_recognized": true/false,
        "has_official_elements": true/false
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