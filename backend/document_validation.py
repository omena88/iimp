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
        """Valida documento SME usando IA"""
        if not self.validate_file_type(file):
            return {
                "valid": False,
                "error": "Tipo de archivo no válido. Solo se permiten PDF, JPG y PNG."
            }
        
        # Verificar si Gemini AI está configurado
        if GEMINI_API_KEY == 'YOUR_GEMINI_API_KEY_HERE':
            return {
                "valid": True,  # Validación básica sin IA
                "validation_type": "SME",
                "document_name": file.filename,
                "result": {
                    "valid": True,
                    "confidence": 50,
                    "overall_assessment": "Validación básica completada (IA no configurada)",
                    "criteria_met": [],
                    "recommendations": ["Configure GEMINI_API_KEY para validación avanzada con IA"]
                }
            }
        
        try:
            file_content = await file.read()
            
            # Criterios de validación SME
            sme_criteria = [
                "El documento debe ser oficial y estar emitido por una institución reconocida",
                f"El nombre en el documento debe coincidir con: {first_name} {last_name}",
                "El documento debe estar vigente y no vencido",
                "El documento debe ser legible y de buena calidad",
                "El documento debe ser auténtico y no alterado",
                "Debe ser un documento que certifique membresía o afiliación SME (Pequeña y Mediana Empresa)"
            ]
            
            prompt = f"""
            Analiza este documento para validar si cumple con los criterios de validación SME.
            
            Criterios a evaluar:
            {chr(10).join([f"- {criterio}" for criterio in sme_criteria])}
            
            Responde en formato JSON con la siguiente estructura:
            {{
                "valid": true/false,
                "confidence": 0-100,
                "criteria_met": [
                    {{
                        "criterion": "descripción del criterio",
                        "met": true/false,
                        "explanation": "explicación detallada"
                    }}
                ],
                "overall_assessment": "evaluación general del documento",
                "recommendations": ["lista de recomendaciones si aplica"]
            }}
            """
            
            if file.content_type == 'application/pdf':
                # Procesar PDF
                text_content = self.extract_text_from_pdf(file_content)
                response = self.model.generate_content([prompt, f"Contenido del documento: {text_content}"])
            else:
                # Procesar imagen
                img_base64 = self.process_image(file_content)
                image_part = {
                    "mime_type": "image/jpeg",
                    "data": img_base64
                }
                response = self.model.generate_content([prompt, image_part])
            
            # Procesar respuesta de Gemini
            result_text = response.text
            
            # Intentar parsear JSON de la respuesta
            try:
                import json
                # Limpiar la respuesta para extraer solo el JSON
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}') + 1
                json_str = result_text[start_idx:end_idx]
                result = json.loads(json_str)
            except:
                # Si no se puede parsear, crear respuesta básica
                result = {
                    "valid": "válido" in result_text.lower() or "cumple" in result_text.lower(),
                    "confidence": 75,
                    "overall_assessment": result_text,
                    "criteria_met": [],
                    "recommendations": []
                }
            
            return {
                "validation_type": "SME",
                "document_name": file.filename,
                "result": result
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Error en validación SME: {str(e)}"
            }
    
    async def validate_academic_document(self, file: UploadFile, first_name: str, last_name: str, doc_type: str, doc_number: str) -> Dict[str, Any]:
        """
        Valida un documento académico (estudiante o docente) usando Gemini AI
        """
        try:
            # Validar tipo de archivo
            if not self.validate_file_type(file):
                return {
                    "valid": False,
                    "reason": "Tipo de archivo no válido. Solo se permiten PDF, JPG, JPEG, PNG",
                    "details": {
                        "file_type_valid": False,
                        "content_analysis": None
                    }
                }

            # Determinar tipo de validación
            if doc_type.lower() == "teacher" or doc_type.lower() == "docente":
                validation_type = "Academic - Teacher"
            else:
                validation_type = "Academic - Student"
            
            # Verificar si Gemini AI está configurado
            if GEMINI_API_KEY == 'YOUR_GEMINI_API_KEY_HERE':
                return {
                    "valid": True,  # Validación básica sin IA
                    "reason": "Validación básica completada (IA no configurada)",
                    "details": {
                        "file_type_valid": True,
                        "content_analysis": {
                            "note": "Gemini AI no configurado, validación básica aplicada",
                            "file_received": True,
                            "validation_type": validation_type,
                            "user_data": {
                                "name": f"{first_name} {last_name}",
                                "doc_type": doc_type,
                                "doc_number": doc_number
                            }
                        }
                    }
                }

            # Leer contenido del archivo
            content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            # Extraer texto según el tipo de archivo
            extracted_text = ""
            image_data = None
            
            if file.content_type == 'application/pdf':
                extracted_text = self.extract_text_from_pdf(content)
            else:
                img_base64 = self.process_image(content)
                image_data = {
                    "mime_type": "image/jpeg",
                    "data": img_base64
                }
            
            # Definir criterios según el tipo de documento
            if doc_type.lower() == "teacher" or doc_type.lower() == "docente":
                academic_criteria = [
                    "Debe ser un documento oficial de una institución educativa",
                    "Debe mostrar el nombre completo del docente",
                    "Debe indicar la materia o área de enseñanza",
                    "Debe mostrar la institución donde labora",
                    "Debe ser un documento que certifique la condición de docente o profesor"
                ]
            else:
                academic_criteria = [
                    "Debe ser un documento oficial de una institución educativa",
                    "Debe mostrar el nombre completo del estudiante",
                    "Debe indicar el programa de estudios o carrera",
                    "Debe mostrar la institución donde estudia",
                    "Debe ser un documento que certifique la condición de estudiante"
                ]
            
            prompt = f"""
Analiza este documento académico y determina si es válido para un {validation_type.lower()}.

Criterios de validación:
{chr(10).join([f"{i+1}. {criterio}" for i, criterio in enumerate(academic_criteria)])}

Datos del solicitante:
- Nombre: {first_name} {last_name}
- Tipo de documento: {doc_type}
- Número de documento: {doc_number}

Texto extraído del documento:
{extracted_text}

Responde ÚNICAMENTE en formato JSON con esta estructura:
{{
    "valid": true/false,
    "confidence": 0.0-1.0,
    "reason": "explicación detallada",
    "criteria_met": {{
        "official_document": true/false,
        "name_matches": true/false,
        "institution_info": true/false,
        "academic_status": true/false,
        "document_current": true/false
    }},
    "extracted_info": {{
        "student_name": "nombre si se encuentra",
        "institution": "institución si se encuentra",
        "program": "programa/materia si se encuentra",
        "status": "estado académico si se encuentra"
    }}
}}
"""

            # Llamar a Gemini AI
            if image_data:
                response = self.model.generate_content([prompt, image_data])
            else:
                response = self.model.generate_content([prompt, f"Contenido del documento: {extracted_text}"])

            # Procesar respuesta
            response_text = response.text.strip()
            
            # Extraer JSON de la respuesta
            import json
            try:
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                json_str = response_text[start_idx:end_idx]
                ai_result = json.loads(json_str)
                
                return {
                    "valid": ai_result.get("valid", False),
                    "reason": ai_result.get("reason", "Análisis completado"),
                    "details": {
                        "file_type_valid": True,
                        "content_analysis": ai_result,
                        "ai_confidence": ai_result.get("confidence", 0.0),
                        "validation_type": validation_type
                    }
                }
                
            except json.JSONDecodeError:
                return {
                    "valid": False,
                    "reason": "Error al procesar la respuesta del análisis de IA",
                    "details": {
                        "file_type_valid": True,
                        "content_analysis": {"raw_response": response_text},
                        "validation_type": validation_type
                    }
                }

        except Exception as e:
            return {
                "valid": False,
                "reason": f"Error durante la validación: {str(e)}",
                "details": {
                    "error": str(e)
                }
            }

# Instancia global del validador
document_validator = DocumentValidator()