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
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())
    
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
                # Parse multipart/form-data
                fields = {}
                files = {}

                def on_field(field):
                    fields[field.field_name.decode()] = field.value.decode()

                def on_file(file):
                    files[file.field_name.decode()] = {
                        'name': file.file_name.decode(),
                        'file_object': file.file_object
                    }
                
                multipart_headers = {
                    'Content-Type': self.headers['Content-Type'],
                    'Content-Length': self.headers['Content-Length']
                }
                multipart.parse_form(multipart_headers, self.rfile, on_field, on_file)

                # Extract data
                validation_type = fields.get('validationType', 'unknown')
                first_name = fields.get('firstName')
                last_name = fields.get('lastName')
                doc_type = fields.get('docType')
                doc_number = fields.get('docNumber')
                
                print(f"Validando documento: tipo={validation_type}, nombre={first_name}, apellido={last_name}, doc_tipo={doc_type}, doc_numero={doc_number}")

                time.sleep(2) # Simulate delay

                # Verificar inscripciones existentes si se proporcionan datos de documento
                existing_inscriptions = []
                if doc_type and doc_number:
                    existing_inscriptions = self.check_existing_inscriptions(doc_type, doc_number)
                    if existing_inscriptions:
                        print(f"Inscripciones encontradas: {existing_inscriptions}")

                # Verificar si se proporcionó un archivo de documento para validación con IA
                document_file = files.get('file')  # El frontend envía el archivo con la clave 'file'
                
                if document_file and validation_type in ['sme', 'academic']:
                    # Usar validación con IA si se proporciona archivo
                    try:
                        # Crear objeto UploadFile simulado
                        class MockUploadFile:
                            def __init__(self, file_obj, filename, content_type):
                                self.file = file_obj
                                self.filename = filename
                                self.content_type = content_type
                            
                            async def read(self):
                                content = self.file.read()
                                self.file.seek(0)  # Reset para futuras lecturas
                                return content
                        
                        mock_file = MockUploadFile(
                            document_file['file_object'],
                            document_file['name'],
                            document_file.get('content_type', 'application/octet-stream')
                        )
                        
                        # Ejecutar validación con IA
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            if validation_type == 'sme':
                                if first_name and last_name and doc_type and doc_number:
                                    ai_result = loop.run_until_complete(
                                        document_validator.validate_sme_document(mock_file, first_name, last_name, doc_type, doc_number)
                                    )
                                else:
                                    ai_result = {
                                        "valid": False,
                                        "reason": "Se requieren nombre, apellido, tipo y número de documento para validación SME"
                                    }
                            else:  # academic
                                if first_name and last_name and doc_type and doc_number:
                                    ai_result = loop.run_until_complete(
                                        document_validator.validate_academic_document(mock_file, first_name, last_name, doc_type, doc_number)
                                    )
                                else:
                                    ai_result = {
                                        "valid": False,
                                        "reason": "Se requieren nombre, apellido, tipo y número de documento para validación académica"
                                    }
                            
                            # Agregar inscripciones existentes al resultado
                            if existing_inscriptions and 'details' in ai_result:
                                ai_result['details']['existing_inscriptions'] = existing_inscriptions
                            elif existing_inscriptions:
                                ai_result['existing_inscriptions'] = existing_inscriptions
                            
                            self._send_json_response(ai_result)
                        finally:
                            loop.close()
                    except Exception as e:
                        print(f"Error en validación con IA: {str(e)}")
                        # Fallback a validación básica
                        self._basic_validation(validation_type, first_name, last_name, existing_inscriptions)
                else:
                    # Validación básica sin archivo o para otros tipos
                    self._basic_validation(validation_type, first_name, last_name, existing_inscriptions)
            
            except Exception as e:
                print(f"Error en validación de documento: {str(e)}")
                import traceback
                traceback.print_exc()
                self._send_json_response({"detail": f"Error interno del servidor: {str(e)}"}, 500)
        
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
        """Validación básica sin IA (fallback)"""
        if validation_type == 'sme':
            if first_name and last_name:
                response_data = {
                    "valid": True,
                    "reason": "Documento SME validado correctamente (validación básica)"
                }
                if existing_inscriptions:
                    response_data["existing_inscriptions"] = existing_inscriptions
                self._send_json_response(response_data)
            else:
                self._send_json_response({
                    "valid": False,
                    "reason": "Faltan datos para la validación del documento SME"
                }, 400)
        
        elif validation_type == 'academic':
            response_data = {
                "valid": True,
                "reason": "Documento académico validado correctamente (validación básica)"
            }
            if existing_inscriptions:
                response_data["existing_inscriptions"] = existing_inscriptions
            self._send_json_response(response_data)
        
        else:
            response_data = {
                "valid": True,
                "reason": "Documento validado correctamente (validación básica)"
            }
            if existing_inscriptions:
                response_data["existing_inscriptions"] = existing_inscriptions
            self._send_json_response(response_data)
    
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