// Configuración de validación de documentos
// Este archivo configura los endpoints para la validación de documentos

(function() {
    'use strict';
    
    // Configuración base
    const BASE_URL = window.location.origin;
    const API_BASE = `${BASE_URL}/api/v1`;
    
    // Configuración de validación
    const ValidationConfig = {
        // URLs de los endpoints específicos
        endpoints: {
            sme: `${API_BASE}/validate-sme-document`,
            academic: `${API_BASE}/validate-academic-document`,
            general: `${API_BASE}/validate-document` // Fallback para compatibilidad
        },
        
        // Método principal para validar documentos
        async validateDocument(formData, validationType = 'general') {
            try {
                console.log(`Validando documento - Tipo: ${validationType}`);
                
                // Determinar el endpoint correcto
                let endpoint;
                let requestFormData = new FormData();
                
                if (validationType === 'sme') {
                    endpoint = this.endpoints.sme;
                    // Mapear campos para el endpoint SME
                    requestFormData.append('document', formData.get('file'));
                    requestFormData.append('user_name', formData.get('firstName'));
                    requestFormData.append('user_lastname', formData.get('lastName'));
                } else if (validationType === 'academic') {
                    endpoint = this.endpoints.academic;
                    // Mapear campos para el endpoint académico
                    requestFormData.append('document', formData.get('file'));
                    requestFormData.append('user_name', formData.get('firstName'));
                    requestFormData.append('user_lastname', formData.get('lastName'));
                    requestFormData.append('academic_type', formData.get('academicType') || 'student');
                } else {
                    // Usar endpoint general como fallback
                    endpoint = this.endpoints.general;
                    // Mantener la estructura original para compatibilidad
                    for (let [key, value] of formData.entries()) {
                        requestFormData.append(key, value);
                    }
                }
                
                console.log(`Enviando petición a: ${endpoint}`);
                
                // Realizar la petición
                const response = await fetch(endpoint, {
                    method: 'POST',
                    body: requestFormData
                });
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.error(`Error HTTP ${response.status}:`, errorText);
                    throw new Error(`Error del servidor: ${response.status}`);
                }
                
                const result = await response.json();
                console.log('Respuesta del servidor:', result);
                
                return result;
                
            } catch (error) {
                console.error('Error en validación:', error);
                throw error;
            }
        },
        
        // Método para obtener configuración del servidor
        async getConfig() {
            try {
                const response = await fetch(`${API_BASE}/config`);
                if (response.ok) {
                    return await response.json();
                }
            } catch (error) {
                console.warn('No se pudo obtener configuración del servidor:', error);
            }
            return null;
        }
    };
    
    // Exponer la configuración globalmente
    window.validationConfig = ValidationConfig;
    
    // Inicializar configuración al cargar la página
    document.addEventListener('DOMContentLoaded', async function() {
        console.log('Inicializando configuración de validación...');
        
        try {
            const config = await ValidationConfig.getConfig();
            if (config) {
                console.log('Configuración del servidor obtenida:', config);
            }
        } catch (error) {
            console.warn('Error al obtener configuración:', error);
        }
        
        console.log('Configuración de validación lista');
    });
    
})();