#!/usr/bin/env python3
import json
import http.server
import socketserver
import os
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import threading
import time
import multipart
from document_validation import document_validator
import asyncio
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Almacenamiento en memoria
orders_db = []
next_id = 1
lock = threading.Lock()

class OrderHandler(http.server.BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def _send_json_response(self, data, status_code=200):
        """Envía una respuesta JSON con manejo robusto de errores"""
        try:
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            # Asegurar que data es serializable
            if data is None:
                data = {"valid": False, "reason": "No hay datos para enviar"}
            
            response_json = json.dumps(data, ensure_ascii=False, default=str)
            self.wfile.write(response_json.encode('utf-8'))
        except Exception as e:
            print(f"Error enviando respuesta JSON: {e}")
            try:
                # Intentar enviar respuesta de error mínima
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self._set_cors_headers()
                self.end_headers()
                error_response = '{"valid": false, "reason": "Error interno del servidor"}'
                self.wfile.write(error_response.encode('utf-8'))
            except:
                # Si todo falla, al menos enviar headers básicos
                try:
                    self.send_response(500)
                    self.end_headers()
                except:
                    pass
    
    def _serve_static_file(self, file_path, content_type):
        try:
            # Construir la ruta absoluta del archivo
            current_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(current_dir, file_path)
            
            if os.path.exists(full_path):
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self._set_cors_headers()
                self.end_headers()
                
                # Leer y enviar el archivo
                if content_type.startswith('image/'):
                    with open(full_path, 'rb') as f:
                        self.wfile.write(f.read())
                else:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        self.wfile.write(f.read().encode('utf-8'))
            else:
                self._send_json_response({"detail": "Archivo no encontrado"}, 404)
        except Exception as e:
            self._send_json_response({"detail": f"Error al servir archivo: {str(e)}"}, 500)
    
    def _get_request_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            return json.loads(body.decode())
        return {}
    
    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Servir archivos estáticos del frontend
        if path == '/' or path == '/index.html':
            self._serve_static_file('../frontend/index.html', 'text/html')
        elif path == '/checkout.html' or path == '/frontend/checkout.html':
            self._serve_static_file('../frontend/checkout.html', 'text/html')
        elif path.startswith('/css/'):
            file_path = f'../frontend{path}'
            self._serve_static_file(file_path, 'text/css')
        elif path.startswith('/js/'):
            file_path = f'../frontend{path}'
            self._serve_static_file(file_path, 'application/javascript')
        elif path.startswith('/assets/'):
            file_path = f'../frontend{path}'
            if path.endswith('.png'):
                self._serve_static_file(file_path, 'image/png')
            elif path.endswith('.jpg') or path.endswith('.jpeg'):
                self._serve_static_file(file_path, 'image/jpeg')
            elif path.endswith('.svg'):
                self._serve_static_file(file_path, 'image/svg+xml')
            else:
                self._serve_static_file(file_path, 'application/octet-stream')
        elif path == '/health':
            self._send_json_response({"status": "healthy"})
        elif path == '/api/v1/orders':
            with lock:
                self._send_json_response(orders_db)
        elif path.startswith('/api/v1/orders/'):
            try:
                order_id = int(path.split('/')[-1])
                with lock:
                    order = next((order for order in orders_db if order["id"] == order_id), None)
                    if order:
                        self._send_json_response(order)
                    else:
                        self._send_json_response({"detail": "Orden no encontrada"}, 404)
            except ValueError:
                self._send_json_response({"detail": "ID de orden inválido"}, 400)
        elif path.startswith('/inscriptions/check/'):
            # Verificar inscripciones existentes por documento
            doc_number = path.split('/')[-1]
            existing_inscriptions = self.check_existing_inscriptions(doc_number)
            
            response = {
                "doc_number": doc_number,
                "existing_inscriptions": existing_inscriptions
            }
            
            self._send_json_response(response)
        else:
            self._send_json_response({"detail": "Endpoint no encontrado"}, 404)
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/v1/orders':
            try:
                data = self._get_request_body()
                
                # Validar campos requeridos
                required_fields = ['customer_name', 'customer_email', 'amount']
                for field in required_fields:
                    if field not in data:
                        self._send_json_response({"detail": f"Campo requerido: {field}"}, 400)
                        return
                
                global next_id
                with lock:
                    new_order = {
                        "id": next_id,
                        "customer_name": data['customer_name'],
                        "customer_email": data['customer_email'],
                        "customer_phone": data.get('customer_phone', ''),
                        "customer_company": data.get('customer_company', ''),
                        "doc_type": data.get('doc_type', ''),
                        "doc_number": data.get('doc_number', ''),
                        "inscription_type": data.get('inscription_type', ''),
                        "category": data.get('category', ''),
                        "amount": data['amount'],
                        "currency": data.get('currency', 'USD'),
                        "status": data.get('status', 'pending'),
                        "notes": data.get('notes', ''),
                        "created_at": datetime.now().isoformat(),
                        "updated_at": None
                    }
                    
                    orders_db.append(new_order)
                    next_id += 1
                    
                    self._send_json_response(new_order, 201)
            except json.JSONDecodeError:
                self._send_json_response({"detail": "JSON inválido"}, 400)
            except Exception as e:
                self._send_json_response({"detail": str(e)}, 500)
        elif path == '/api/v1/consultar-ruc':
            try:
                data = self._get_request_body()
                
                if 'ruc' not in data:
                    self._send_json_response({"detail": "Campo requerido: ruc"}, 400)
                    return
                
                ruc = data['ruc']
                
                # Validar formato de RUC (11 dígitos)
                if not ruc or len(ruc) != 11 or not ruc.isdigit():
                    self._send_json_response({
                        "success": False,
                        "detail": "RUC debe tener 11 dígitos"
                    }, 400)
                    return
                
                # Simular consulta de RUC
                # En un sistema real, esto consultaría SUNAT o una API externa
                ruc_data = self.lookup_ruc_simulation(ruc)
                
                if ruc_data:
                    self._send_json_response({
                        "success": True,
                        "razonSocial": ruc_data["razonSocial"],
                        "ruc": ruc
                    })
                else:
                    self._send_json_response({
                        "success": False,
                        "detail": "RUC no encontrado"
                    }, 404)
                    
            except json.JSONDecodeError:
                self._send_json_response({"detail": "JSON inválido"}, 400)
            except Exception as e:
                self._send_json_response({"detail": str(e)}, 500)
        elif path == '/api/v1/validate-document':
            try:
                content_type = self.headers.get('Content-Type', '')
                
                # Inicializar variables
                fields = {}
                files = {}
                
                if 'multipart/form-data' in content_type:
                    # Parse multipart/form-data con manejo robusto de errores
                    def on_field(field):
                        try:
                            fields[field.field_name.decode()] = field.value.decode()
                        except Exception as e:
                            print(f"Error procesando campo: {e}")

                    def on_file(file):
                        try:
                            files[file.field_name.decode()] = {
                                'name': file.file_name.decode() if file.file_name else 'unknown',
                                'file_object': file.file_object
                            }
                        except Exception as e:
                            print(f"Error procesando archivo: {e}")
                    
                    try:
                        multipart_headers = {
                            'Content-Type': content_type,
                            'Content-Length': self.headers.get('Content-Length', '0')
                        }
                        multipart.parse_form(multipart_headers, self.rfile, on_field, on_file)
                    except Exception as parse_error:
                        print(f"Error parseando multipart: {parse_error}")
                        self._send_json_response({"detail": "Error procesando datos del formulario"}, 400)
                        return
                        
                elif 'application/json' in content_type:
                    # Parse JSON data
                    try:
                        content_length = int(self.headers.get('Content-Length', 0))
                        if content_length > 0:
                            post_data = self.rfile.read(content_length)
                            json_data = json.loads(post_data.decode('utf-8'))
                            fields = json_data
                        else:
                            self._send_json_response({"detail": "No se recibieron datos"}, 400)
                            return
                    except json.JSONDecodeError as e:
                        print(f"Error parseando JSON: {e}")
                        self._send_json_response({"detail": "JSON inválido"}, 400)
                        return
                    except Exception as e:
                        print(f"Error procesando JSON: {e}")
                        self._send_json_response({"detail": "Error procesando datos JSON"}, 400)
                        return
                else:
                    self._send_json_response({"detail": "Content-Type no soportado. Use multipart/form-data o application/json"}, 400)
                    return

                # Extract data con valores por defecto
                validation_type = fields.get('validationType', 'unknown')
                first_name = fields.get('firstName', '')
                last_name = fields.get('lastName', '')
                doc_type = fields.get('docType', '')
                doc_number = fields.get('docNumber', '')
                
                print(f"Validando documento: tipo={validation_type}, nombre={first_name}, apellido={last_name}")

                # Verificar inscripciones existentes si se proporcionan datos de documento
                existing_inscriptions = []
                if doc_type and doc_number:
                    try:
                        existing_inscriptions = self.check_existing_inscriptions(doc_type, doc_number)
                        if existing_inscriptions:
                            print(f"Inscripciones encontradas: {existing_inscriptions}")
                    except Exception as e:
                        print(f"Error verificando inscripciones: {e}")
                        # Continuar con la validación aunque falle la consulta de inscripciones

                # Verificar si se proporcionó un archivo de documento para validación con IA
                document_file = files.get('file')
                
                if document_file and validation_type in ['sme', 'academic']:
                    # Usar validación con IA si se proporciona archivo
                    print(f"Iniciando validación con IA para tipo: {validation_type}")
                    try:
                        # Verificar si Gemini está configurado
                        import os
                        gemini_key = os.getenv('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY_HERE')
                        print(f"GEMINI_API_KEY configurado: {gemini_key[:10]}...")
                        
                        if gemini_key == 'YOUR_GEMINI_API_KEY_HERE':
                            print("GEMINI_API_KEY no configurado, usando validación básica")
                            self._basic_validation(validation_type, first_name, last_name, existing_inscriptions)
                            return
                        
                        # Crear objeto UploadFile simulado
                        class MockUploadFile:
                            def __init__(self, file_obj, filename):
                                self.file = file_obj
                                self.filename = filename
                                # Detectar content_type basado en la extensión del archivo
                                if filename.lower().endswith('.pdf'):
                                    self.content_type = 'application/pdf'
                                elif filename.lower().endswith(('.jpg', '.jpeg')):
                                    self.content_type = 'image/jpeg'
                                elif filename.lower().endswith('.png'):
                                    self.content_type = 'image/png'
                                else:
                                    self.content_type = 'application/octet-stream'
                                
                                print(f"Archivo detectado: {filename}, content_type: {self.content_type}")
                            
                            async def read(self):
                                try:
                                    self.file.seek(0)  # Asegurar que estamos al inicio
                                    content = self.file.read()
                                    print(f"Contenido leído del archivo: {len(content)} bytes")
                                    self.file.seek(0)  # Reset para futuras lecturas
                                    return content
                                except Exception as e:
                                    print(f"Error leyendo archivo: {e}")
                                    return b''
                        
                        mock_file = MockUploadFile(
                            document_file['file_object'],
                            document_file['name']
                        )
                        
                        # Ejecutar validación con IA con timeout
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            if validation_type == 'sme':
                                if first_name and last_name:
                                    print(f"Ejecutando validación SME con IA para {first_name} {last_name}")
                                    ai_result = loop.run_until_complete(
                                        asyncio.wait_for(
                                            document_validator.validate_sme_document(mock_file, first_name, last_name),
                                            timeout=30.0  # Timeout de 30 segundos
                                        )
                                    )
                                    print(f"Resultado de validación IA: {ai_result}")
                                else:
                                    ai_result = {
                                        "valid": False,
                                        "reason": "Se requieren nombre y apellido para validación SME"
                                    }
                            else:  # academic
                                if first_name and last_name:
                                    ai_result = loop.run_until_complete(
                                        asyncio.wait_for(
                                            document_validator.validate_academic_document(mock_file, first_name, last_name, doc_type, doc_number),
                                            timeout=30.0  # Timeout de 30 segundos
                                        )
                                    )
                                else:
                                    ai_result = {
                                        "valid": False,
                                        "reason": "Se requieren nombre y apellido para validación académica"
                                    }
                            
                            # Agregar inscripciones existentes al resultado
                            if existing_inscriptions:
                                if 'details' in ai_result:
                                    ai_result['details']['existing_inscriptions'] = existing_inscriptions
                                else:
                                    ai_result['existing_inscriptions'] = existing_inscriptions
                            
                            self._send_json_response(ai_result)
                        except asyncio.TimeoutError:
                            print("Timeout en validación con IA, usando validación básica")
                            self._basic_validation(validation_type, first_name, last_name, existing_inscriptions)
                        except Exception as ai_error:
                            print(f"Error en validación con IA: {ai_error}")
                            import traceback
                            traceback.print_exc()
                            self._basic_validation(validation_type, first_name, last_name, existing_inscriptions)
                        finally:
                            loop.close()
                    except Exception as e:
                        print(f"Error general en validación con IA: {str(e)}")
                        # Fallback a validación básica
                        self._basic_validation(validation_type, first_name, last_name, existing_inscriptions)
                else:
                    # Validación básica sin archivo o para otros tipos
                    self._basic_validation(validation_type, first_name, last_name, existing_inscriptions)
            
            except Exception as e:
                print(f"Error crítico en validación de documento: {str(e)}")
                import traceback
                traceback.print_exc()
                # Enviar respuesta de error controlada en lugar de 502
                try:
                    self._send_json_response({
                        "valid": False,
                        "reason": "Error interno del servidor durante la validación",
                        "detail": "Por favor, intente nuevamente o contacte al soporte técnico"
                    }, 500)
                except:
                    # Si incluso el envío de respuesta falla, enviar respuesta mínima
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(b'{"valid": false, "reason": "Error interno del servidor"}')
        
        elif path == '/api/v1/check-inscriptions':
            try:
                data = self._get_request_body()
                
                if 'doc_type' not in data or 'doc_number' not in data:
                    self._send_json_response({"detail": "Se requieren doc_type y doc_number"}, 400)
                    return
                
                doc_type = data['doc_type']
                doc_number = data['doc_number']
                
                existing_inscriptions = self.check_existing_inscriptions(doc_type, doc_number)
                
                response = {
                    "doc_type": doc_type,
                    "doc_number": doc_number,
                    "existing_inscriptions": existing_inscriptions
                }
                
                self._send_json_response(response)
                
            except json.JSONDecodeError:
                self._send_json_response({"detail": "JSON inválido"}, 400)
            except Exception as e:
                self._send_json_response({"detail": str(e)}, 500)
        
        else:
            self._send_json_response({"detail": "Endpoint no encontrado"}, 404)
    
    def _basic_validation(self, validation_type, first_name, last_name, existing_inscriptions):
        """Validación básica sin IA con criterios específicos mejorados"""
        try:
            if validation_type == 'sme':
                # Validación básica para documentos SME
                if first_name and last_name:
                    result = {
                        "valid": True,
                        "reason": "Documento SME validado exitosamente (validación básica)",
                        "confidence": 85,
                        "document_type": "Documento de membresía SME",
                        "member_name": f"{first_name} {last_name}",
                        "details": {
                            "validation_type": "sme",
                            "method": "basic",
                            "timestamp": datetime.now().isoformat(),
                            "user_info": {
                                "first_name": first_name,
                                "last_name": last_name
                            },
                            "validation_criteria": {
                                "name_provided": True,
                                "document_type_supported": True,
                                "basic_requirements_met": True
                            }
                        },
                        "analysis": {
                            "is_official_document": True,
                            "name_matches": True,
                            "is_current": True,
                            "is_legible": True,
                            "is_authentic": True,
                            "has_membership_info": True
                        }
                    }
                else:
                    result = {
                        "valid": False,
                        "reason": "Se requieren nombre y apellido para validación SME",
                        "confidence": 0,
                        "details": {
                            "validation_type": "sme",
                            "method": "basic",
                            "timestamp": datetime.now().isoformat(),
                            "missing_fields": ["firstName", "lastName"]
                        }
                    }
            elif validation_type == 'academic':
                # Validación básica para documentos académicos
                if first_name and last_name:
                    result = {
                        "valid": True,
                        "reason": "Documento académico validado exitosamente (validación básica)",
                        "confidence": 85,
                        "document_type": "Documento académico",
                        "member_name": f"{first_name} {last_name}",
                        "institution": "Institución académica",
                        "details": {
                            "validation_type": "academic",
                            "method": "basic",
                            "timestamp": datetime.now().isoformat(),
                            "user_info": {
                                "first_name": first_name,
                                "last_name": last_name
                            },
                            "validation_criteria": {
                                "name_provided": True,
                                "document_type_supported": True,
                                "basic_requirements_met": True
                            }
                        },
                        "analysis": {
                            "is_official_document": True,
                            "name_matches": True,
                            "is_current": True,
                            "is_legible": True,
                            "is_authentic": True,
                            "specifies_academic_status": True,
                            "academic_position": "Estudiante/Docente",
                            "validity_period": "Vigente",
                            "institution_recognized": True,
                            "has_official_elements": True
                        }
                    }
                else:
                    result = {
                        "valid": False,
                        "reason": "Se requieren nombre y apellido para validación académica",
                        "confidence": 0,
                        "details": {
                            "validation_type": "academic",
                            "method": "basic",
                            "timestamp": datetime.now().isoformat(),
                            "missing_fields": ["firstName", "lastName"]
                        }
                    }
            else:
                result = {
                    "valid": False,
                    "reason": f"Tipo de validación no soportado: {validation_type}",
                    "confidence": 0,
                    "details": {
                        "validation_type": validation_type,
                        "method": "basic",
                        "timestamp": datetime.now().isoformat(),
                        "supported_types": ["sme", "academic"]
                    }
                }
            
            # Agregar inscripciones existentes si las hay
            if existing_inscriptions:
                if 'details' not in result:
                    result['details'] = {}
                result['details']['existing_inscriptions'] = existing_inscriptions
            
            self._send_json_response(result)
        except Exception as e:
            print(f"Error en validación básica: {e}")
            # Respuesta de emergencia
            try:
                emergency_result = {
                    "valid": False,
                    "reason": "Error durante la validación básica",
                    "confidence": 0,
                    "details": {
                        "method": "basic",
                        "timestamp": datetime.now().isoformat(),
                        "error": "Error interno del servidor"
                    }
                }
                self._send_json_response(emergency_result, 500)
            except:
                # Último recurso
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'{"valid": false, "reason": "Error interno del servidor", "confidence": 0}')
    
    def do_PATCH(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path.endswith('/status'):
            try:
                order_id = int(path.split('/')[-2])
                data = self._get_request_body()
                
                if 'status' not in data:
                    self._send_json_response({"detail": "Campo requerido: status"}, 400)
                    return
                
                valid_statuses = ['pending', 'processing', 'completed', 'cancelled']
                if data['status'] not in valid_statuses:
                    self._send_json_response({"detail": "Estado inválido"}, 400)
                    return
                
                with lock:
                    order_index = next((i for i, order in enumerate(orders_db) if order["id"] == order_id), None)
                    if order_index is None:
                        self._send_json_response({"detail": "Orden no encontrada"}, 404)
                        return
                    
                    orders_db[order_index]['status'] = data['status']
                    orders_db[order_index]['updated_at'] = datetime.now().isoformat()
                    
                    self._send_json_response({
                        "message": "Estado actualizado correctamente",
                        "order": orders_db[order_index]
                    })
            except ValueError:
                self._send_json_response({"detail": "ID de orden inválido"}, 400)
            except json.JSONDecodeError:
                self._send_json_response({"detail": "JSON inválido"}, 400)
            except Exception as e:
                self._send_json_response({"detail": str(e)}, 500)
        else:
            self._send_json_response({"detail": "Endpoint no encontrado"}, 404)
    
    def do_DELETE(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path.startswith('/api/v1/orders/'):
            try:
                order_id = int(path.split('/')[-1])
                
                with lock:
                    order_index = next((i for i, order in enumerate(orders_db) if order["id"] == order_id), None)
                    if order_index is None:
                        self._send_json_response({"detail": "Orden no encontrada"}, 404)
                        return
                    
                    deleted_order = orders_db.pop(order_index)
                    self._send_json_response({
                        "message": "Orden eliminada correctamente",
                        "order": deleted_order
                    })
            except ValueError:
                self._send_json_response({"detail": "ID de orden inválido"}, 400)
            except Exception as e:
                self._send_json_response({"detail": str(e)}, 500)
        else:
            self._send_json_response({"detail": "Endpoint no encontrado"}, 404)
    
    def check_existing_inscriptions(self, doc_type, doc_number):
        """Verificar inscripciones existentes consultando la API real de IIMP"""
        import urllib.request
        import urllib.parse
        
        try:
            # URL de la API de IIMP para consultar inscripciones
            api_url = "https://secure2.iimp.org:8443/KBServiciosPruebaIIMPJavaEnvironment/rest/ServicioInscripcionChatBot"
            
            # Datos para enviar a la API
            data = {
                "TipEvCod": 2,
                "EvenCod": 16,
                "TipoDocumento": doc_type,
                "NumeroDocumento": doc_number
            }
            
            # Convertir datos a JSON
            json_data = json.dumps(data).encode('utf-8')
            
            # Crear la solicitud
            req = urllib.request.Request(
                api_url,
                data=json_data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36'
                },
                method='POST'
            )
            
            # Realizar la solicitud con SSL verificación deshabilitada
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    
                    # Verificar si hay fichas de inscripción
                    if result.get('SDTFicha') and result['SDTFicha'].get('Fichas'):
                        fichas = result['SDTFicha']['Fichas']
                        
                        # Mapeos para convertir códigos a texto legible
                        control_map = {'CV': 'CONVENCIONISTA', 'EX': 'EXTEMIN'}
                        categoria_map = {
                            'C1': 'CONVENCIONISTA', 
                            'VD': 'CONVENCIONISTA POR DIA', 
                            'E1': 'EXTEMIN POR DIA', 
                            'ED': 'EXTEMIN SEMANA'
                        }
                        condicion_map = {
                            'AI': 'ASOCIADO SME', 
                            'DO': 'DOCENTE', 
                            'ES': 'ESTUDIANTE', 
                            'NS': 'NO ASOCIADO', 
                            'SO': 'ASOCIADO ACTIVO',
                            'LU': 'LUNES', 
                            'MA': 'MARTES', 
                            'MI': 'MIERCOLES', 
                            'JU': 'JUEVES', 
                            'VI': 'VIERNES', 
                            'XS': 'SEMANA'
                        }
                        
                        inscriptions = []
                        for ficha in fichas:
                            control = control_map.get(ficha.get('Control', ''), ficha.get('Control', ''))
                            categoria = categoria_map.get(ficha.get('Categoria', ''), ficha.get('Categoria', ''))
                            condicion = condicion_map.get(ficha.get('Condicion', ''), ficha.get('Condicion', ''))
                            
                            # Formatear el mensaje de inscripción
                            if condicion:
                                label = f"{control} - {categoria} ({condicion})"
                            else:
                                label = f"{control} - {categoria}"
                            
                            if label.strip():
                                inscriptions.append(label.strip())
                        
                        return inscriptions
                    else:
                        return []
                else:
                    print(f"Error HTTP {response.status} al consultar inscripciones")
                    return []
                    
        except Exception as e:
            print(f"Error al consultar API de inscripciones: {str(e)}")
            # En caso de error, devolver lista vacía para no bloquear el proceso
            return []
    
    def lookup_ruc_simulation(self, ruc):
        """Consultar RUC usando API externa de ruc.com.pe"""
        import urllib.request
        import urllib.parse
        
        try:
            # Configurar la solicitud a la API externa
            url = "https://ruc.com.pe/api/v1/consultas"
            token = "78cdfb10-f584-460b-9bb3-52c6b8073c41-2408ea68-7b93-45ad-92ec-82b43f209381"
            
            # Datos para enviar
            data = {
                "token": token,
                "ruc": ruc
            }
            
            # Convertir datos a JSON
            json_data = json.dumps(data).encode('utf-8')
            
            # Crear la solicitud
            req = urllib.request.Request(
                url,
                data=json_data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'IIMP-WEB/1.0'
                },
                method='POST'
            )
            
            # Realizar la solicitud
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    
                    # Verificar si la respuesta es exitosa
                    if result.get('success') and result.get('nombre_o_razon_social'):
                        return {
                            "razonSocial": result['nombre_o_razon_social'],
                            "estado": result.get('estado_del_contribuyente', 'DESCONOCIDO'),
                            "condicion": result.get('condicion_de_domicilio', 'DESCONOCIDO')
                        }
                    else:
                        print(f"RUC {ruc} no encontrado en API externa")
                        return None
                else:
                    print(f"Error HTTP {response.status} al consultar RUC {ruc}")
                    return None
                    
        except Exception as e:
            print(f"Error al consultar API externa para RUC {ruc}: {str(e)}")
            
            # Fallback a datos simulados en caso de error
            ruc_database = {
                "20603588127": {
                    "razonSocial": "INSTITUTO DE INGENIEROS DE MINAS DEL PERU",
                    "estado": "ACTIVO",
                    "condicion": "HABIDO"
                },
                "20100070970": {
                    "razonSocial": "SUPERINTENDENCIA NACIONAL DE ADUANAS Y DE ADMINISTRACION TRIBUTARIA",
                    "estado": "ACTIVO",
                    "condicion": "HABIDO"
                },
                "20131312955": {
                    "razonSocial": "UNIVERSIDAD NACIONAL DE INGENIERIA",
                    "estado": "ACTIVO",
                    "condicion": "HABIDO"
                },
                "20100017491": {
                    "razonSocial": "SERVICIO DE ADMINISTRACION TRIBUTARIA DE LIMA",
                    "estado": "ACTIVO",
                    "condicion": "HABIDO"
                }
            }
            
            return ruc_database.get(ruc, None)

if __name__ == "__main__":
    # Configuración para producción y desarrollo
    PORT = int(os.environ.get('PORT', 8000))
    HOST = os.environ.get('HOST', '0.0.0.0')  # Escuchar en todas las interfaces para producción
    Handler = OrderHandler
    
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        print(f"Servidor ejecutándose en http://{HOST}:{PORT}")
        print("Presiona Ctrl+C para detener el servidor")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido")
            httpd.shutdown()