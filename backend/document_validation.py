# DEPRECADO: Este archivo ha sido refactorizado para usar validation_api.py
# Para evitar duplicación de código, ahora importamos la funcionalidad desde validation_api.py

import os
from typing import Dict, Any, Optional
from fastapi import UploadFile, HTTPException
from dotenv import load_dotenv

# Importar el validador desde validation_api.py
try:
    from validation_api import DocumentValidator as ValidationAPIValidator
except ImportError:
    # Fallback si validation_api no está disponible
    print("ADVERTENCIA: No se pudo importar validation_api.py")
    ValidationAPIValidator = None

# Cargar variables de entorno
load_dotenv()

class DocumentValidator:
    """Wrapper para mantener compatibilidad con el código existente"""
    
    def __init__(self):
        if ValidationAPIValidator:
            self._validator = ValidationAPIValidator()
        else:
            self._validator = None
            print("ADVERTENCIA: DocumentValidator no disponible - validation_api.py no encontrado")
        
    def validate_file_type(self, file: UploadFile) -> bool:
        """Valida que el archivo sea PDF, JPG o PNG"""
        if self._validator:
            return self._validator.validate_file_type(file)
        return False
    
    def validate_file_size(self, file_content: bytes) -> bool:
        """Valida el tamaño del archivo"""
        if self._validator:
            return self._validator.validate_file_size(file_content)
        return False
    
    async def validate_sme_document(self, file: UploadFile, first_name: str, last_name: str, doc_type: Optional[str] = None, doc_number: Optional[str] = None) -> Dict[str, Any]:
        """Valida documento SME usando validation_api.py"""
        if not self._validator:
            return {
                "valid": False,
                "reason": "Servicio de validación no disponible.",
                "confidence": 0
            }
        
        try:
            # Validar tipo de archivo
            if not self.validate_file_type(file):
                return {
                    "valid": False,
                    "reason": "Tipo de archivo no válido. Solo se permiten PDF, JPG y PNG.",
                    "confidence": 0
                }
            
            # Leer contenido del archivo
            file_content = await file.read()
            
            # Validar tamaño
            if not self.validate_file_size(file_content):
                return {
                    "valid": False,
                    "reason": "El archivo es demasiado grande. Máximo 10MB.",
                    "confidence": 0
                }
            
            # Usar validation_api.py para la validación
             return self._validator.validate_sme_document(
                 file_content, first_name, last_name, file.content_type
             )
            
        except Exception as e:
            return {
                "valid": False,
                "reason": f"Error en validación SME: {str(e)}",
                "confidence": 0
            }
    
    async def validate_academic_document(self, file: UploadFile, first_name: str, last_name: str, doc_type: str, doc_number: str) -> Dict[str, Any]:
        """
        Valida un documento académico usando validation_api.py
        """
        if not self._validator:
            return {
                "valid": False,
                "reason": "Servicio de validación no disponible.",
                "confidence": 0
            }
        
        try:
            # Validar tipo de archivo
            if not self.validate_file_type(file):
                return {
                    "valid": False,
                    "reason": "Tipo de archivo no válido. Solo se permiten PDF, JPG, JPEG, PNG",
                    "confidence": 0
                }

            # Leer contenido del archivo
            file_content = await file.read()
            
            # Validar tamaño
            if not self.validate_file_size(file_content):
                return {
                    "valid": False,
                    "reason": "El archivo es demasiado grande. Máximo 10MB.",
                    "confidence": 0
                }
            
            # Usar validation_api.py para la validación
             return self._validator.validate_academic_document(
                 file_content, first_name, last_name, doc_type, file.content_type
             )

        except Exception as e:
            return {
                "valid": False,
                "reason": f"Error durante la validación: {str(e)}",
                "confidence": 0
            }

# Instancia global del validador (mantener compatibilidad)
document_validator = DocumentValidator()