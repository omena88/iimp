/**
 * Configuración dinámica para validación de documentos
 * Detecta automáticamente si está en local o producción
 */

class ValidationConfig {
    constructor() {
        this.isProduction = this.detectEnvironment();
        this.apiBaseUrl = this.getApiBaseUrl();
        this.endpoints = this.getEndpoints();
    }

    /**
     * Detecta si estamos en producción o desarrollo
     */
    detectEnvironment() {
        const hostname = window.location.hostname;
        return hostname !== 'localhost' && hostname !== '127.0.0.1' && hostname !== '';
    }

    /**
     * Obtiene la URL base de la API según el entorno
     */
    getApiBaseUrl() {
        if (this.isProduction) {
            // En producción, usar el proxy de nginx en el mismo dominio
            return window.location.origin;
        } else {
            return 'http://localhost:8001';
        }
    }

    /**
     * Obtiene los endpoints de validación
     */
    getEndpoints() {
        return {
            sme: `${this.apiBaseUrl}/api/v1/validate-sme-document`,
            academic: `${this.apiBaseUrl}/api/v1/validate-academic-document`,
            general: `${this.apiBaseUrl}/api/v1/validate-document`,
            config: `${this.apiBaseUrl}/config`
        };
    }

    /**
     * Valida un documento usando la nueva API
     */
    async validateDocument(formData, validationType = 'general') {
        try {
            console.log(`[ValidationConfig] Validando documento tipo: ${validationType}`);
            
            // Determinar el endpoint correcto
            let endpoint;
            if (validationType === 'sme') {
                endpoint = this.endpoints.sme;
            } else if (validationType === 'academic') {
                // Verificar si es teacher o student desde formData
                const academicType = formData.get('academicType');
                endpoint = academicType === 'teacher' ? this.endpoints.academic : this.endpoints.academic;
            } else {
                endpoint = this.endpoints.general;
            }
            
            console.log(`[ValidationConfig] URL: ${endpoint}`);
            console.log(`[ValidationConfig] Entorno: ${this.isProduction ? 'Producción' : 'Desarrollo'}`);

            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData,
                // No establecer Content-Type para multipart/form-data
                headers: {
                    'Accept': 'application/json'
                }
            });

            console.log(`[ValidationConfig] Status: ${response.status}`);

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`[ValidationConfig] Error response:`, errorText);
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log(`[ValidationConfig] Resultado:`, result);
            return result;

        } catch (error) {
            console.error(`[ValidationConfig] Error en validación:`, error);
            throw error;
        }
    }

    /**
     * Obtiene la configuración del servidor
     */
    async getServerConfig() {
        try {
            const response = await fetch(this.endpoints.config);
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.warn('[ValidationConfig] No se pudo obtener configuración del servidor:', error);
        }
        return null;
    }

    /**
     * Verifica la conectividad con la API
     */
    async checkApiHealth() {
        try {
            const response = await fetch(this.apiBaseUrl, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });
            return response.ok;
        } catch (error) {
            console.error('[ValidationConfig] API no disponible:', error);
            return false;
        }
    }

    /**
     * Inicializa la configuración y verifica conectividad
     */
    async initialize() {
        console.log('[ValidationConfig] Inicializando...');
        console.log(`[ValidationConfig] Entorno detectado: ${this.isProduction ? 'Producción' : 'Desarrollo'}`);
        console.log(`[ValidationConfig] API Base URL: ${this.apiBaseUrl}`);

        const isHealthy = await this.checkApiHealth();
        if (!isHealthy) {
            console.warn('[ValidationConfig] API no responde, usando configuración de respaldo');
        }

        const serverConfig = await this.getServerConfig();
        if (serverConfig) {
            console.log('[ValidationConfig] Configuración del servidor:', serverConfig);
        }

        return {
            isHealthy,
            environment: this.isProduction ? 'production' : 'development',
            apiBaseUrl: this.apiBaseUrl,
            endpoints: this.endpoints,
            serverConfig
        };
    }
}

// Crear instancia global
const validationConfig = new ValidationConfig();

// Función de compatibilidad para el código existente
window.validateDocument = async function(formData, validationType = 'general') {
    return await validationConfig.validateDocument(formData, validationType);
};

// Exportar para uso en módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ValidationConfig, validationConfig };
}

// Inicializar automáticamente cuando se carga la página
if (typeof window !== 'undefined') {
    window.addEventListener('DOMContentLoaded', async () => {
        try {
            const initResult = await validationConfig.initialize();
            console.log('[ValidationConfig] Inicialización completada:', initResult);
            
            // Hacer disponible globalmente
            window.validationConfig = validationConfig;
        } catch (error) {
            console.error('[ValidationConfig] Error en inicialización:', error);
        }
    });
}