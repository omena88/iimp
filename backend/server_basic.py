import json
import string
import random
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time

class APIHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        
        # Set CORS headers
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            request_data = json.loads(post_data.decode('utf-8'))
        except:
            request_data = {}
        
        if parsed_path.path == '/api/v1/create-order-link':
            # Generate random short link
            short_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            response = {
                "success": True,
                "short_link": f"https://checkout.iimp.org.pe/{short_id}",
                "order_id": f"ORD-{random.randint(100000, 999999)}",
                "message": "Link de pago generado exitosamente"
            }
            
        elif parsed_path.path == '/api/v1/consultar-ruc':
            ruc = request_data.get('ruc', '')
            response = {
                "success": True,
                "ruc": ruc,
                "razon_social": f"Empresa Ejemplo {ruc[-4:]}",
                "estado": "ACTIVO",
                "condicion": "HABIDO",
                "direccion": "Av. Ejemplo 123, Lima",
                "ubigeo": "150101",
                "departamento": "LIMA",
                "provincia": "LIMA",
                "distrito": "LIMA"
            }
            
        elif parsed_path.path == '/api/v1/check-inscriptions':
            response = {
                "success": True,
                "is_registered": False,
                "message": "Participante no registrado previamente",
                "previous_registrations": []
            }
            
        else:
            response = {"error": "Endpoint not found"}
        
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {"status": "healthy", "message": "API funcionando correctamente"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            # Serve static files from frontend directory
            frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
            
            # Clean the path by removing query parameters
            clean_path = self.path.split('?')[0]
            
            # Handle root path
            if clean_path == '/' or clean_path == '/index.html':
                file_path = os.path.join(frontend_dir, 'index.html')
            elif clean_path == '/checkout.html':
                file_path = os.path.join(frontend_dir, 'checkout.html')
            elif clean_path.startswith('/css/'):
                file_path = os.path.join(frontend_dir, clean_path[1:])
            elif clean_path.startswith('/js/'):
                file_path = os.path.join(frontend_dir, clean_path[1:])
            elif clean_path.startswith('/assets/'):
                file_path = os.path.join(frontend_dir, clean_path[1:])
            else:
                file_path = None
            
            if file_path and os.path.exists(file_path):
                self.send_response(200)
                
                # Set content type based on file extension
                if file_path.endswith('.html'):
                    content_type = 'text/html'
                elif file_path.endswith('.css'):
                    content_type = 'text/css'
                elif file_path.endswith('.js'):
                    content_type = 'application/javascript'
                elif file_path.endswith('.png'):
                    content_type = 'image/png'
                elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
                    content_type = 'image/jpeg'
                else:
                    content_type = 'text/plain'
                
                self.send_header('Content-Type', content_type)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                # Read and serve the file
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<h1>404 - Page Not Found</h1>')

def run_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, APIHandler)
    print(f"Servidor iniciado en http://localhost:8000")
    print("Endpoints disponibles:")
    print("- POST /api/v1/create-order-link")
    print("- POST /api/v1/consultar-ruc")
    print("- POST /api/v1/check-inscriptions")
    print("- GET /health")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()