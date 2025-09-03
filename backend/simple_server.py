#!/usr/bin/env python3
import json
import http.server
import socketserver
import os
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import threading

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
        else:
            self._send_json_response({"detail": "Endpoint no encontrado"}, 404)
    
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
    
    def check_existing_inscriptions(self, doc_number):
        """Simular verificación de inscripciones existentes basado en número de documento"""
        # Simular datos de inscripciones existentes
        # En un sistema real, esto consultaría una base de datos o API externa
        existing_data = {
            "12345678": [
                "CONVENCIONISTA - ASOCIADO ACTIVO (PERUMIN 36)",
                "EXTEMIN - ESTUDIANTE (PERUMIN 35)"
            ],
            "87654321": [
                "CONVENCIONISTA - NO ASOCIADO (PERUMIN 36)"
            ],
            "11223344": [
                "EXTEMIN - DOCENTE (PERUMIN 36)",
                "CONVENCIONISTA - ASOCIADO SME (PERUMIN 35)"
            ]
        }
        
        # Buscar inscripciones por número de documento
        if doc_number in existing_data:
            return existing_data[doc_number]
        
        # Si el documento tiene 8 dígitos, simular que tiene inscripciones
        if len(doc_number) == 8 and doc_number.isdigit():
            return [
                "CONVENCIONISTA - ASOCIADO ACTIVO (PERUMIN 36)",
                "EXTEMIN - ESTUDIANTE (PERUMIN 35)"
            ]
        
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
    PORT = 8000
    Handler = OrderHandler
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Servidor ejecutándose en http://localhost:{PORT}")
        print("Presiona Ctrl+C para detener el servidor")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido")
            httpd.shutdown()