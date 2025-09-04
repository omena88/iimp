#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración para URLs dinámicas y entornos
"""

import os
from typing import Dict, Any

class Config:
    """Configuración de la aplicación"""
    
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.is_production = self.environment == 'production'
        
    # Server configuration
    server_host: str = "0.0.0.0"
    server_port: int = 8001
        
    @property
    def api_base_url(self) -> str:
        """URL base de la API según el entorno"""
        if self.is_production:
            return "https://apis-iimp-web.di8b44.easypanel.host"
        else:
            return "http://localhost:8001"
    
    @property
    def validation_endpoints(self) -> Dict[str, str]:
        """Endpoints de validación"""
        base = self.api_base_url
        return {
            'sme': f"{base}/api/v1/validate-sme-document",
            'academic': f"{base}/api/v1/validate-academic-document",
            'general': f"{base}/api/v1/validate-document"
        }
    
    @property
    def server_config(self) -> Dict[str, Any]:
        """Configuración del servidor"""
        if self.is_production:
            return {
                'host': '0.0.0.0',
                'port': 8001,
                'reload': False,
                'log_level': 'info',
                'workers': 4
            }
        else:
            return {
                'host': 'localhost',
                'port': 8001,
                'reload': True,
                'log_level': 'debug',
                'workers': 1
            }
    
    @property
    def cors_origins(self) -> list:
        """Orígenes permitidos para CORS"""
        if self.is_production:
            return [
                "https://apis-iimp-web.di8b44.easypanel.host",
                "https://iimp-web.di8b44.easypanel.host",
                "https://www.iimp.org.pe",
                "https://iimp.org.pe"
            ]
        else:
            return ["*"]
    
    def get_frontend_config(self) -> Dict[str, str]:
        """Configuración para el frontend"""
        return {
            'API_BASE_URL': self.api_base_url,
            'VALIDATION_ENDPOINT': self.validation_endpoints['general'],
            'SME_ENDPOINT': self.validation_endpoints['sme'],
            'ACADEMIC_ENDPOINT': self.validation_endpoints['academic'],
            'ENVIRONMENT': self.environment
        }

# Instancia global de configuración
config = Config()