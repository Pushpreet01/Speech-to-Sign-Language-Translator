from http.server import BaseHTTPRequestHandler
import sys
import os

# Add the parent directory to the path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Handle GET requests
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Import and run Flask app
        with app.test_client() as client:
            response = client.get(self.path)
            self.wfile.write(response.data)
    
    def do_POST(self):
        # Handle POST requests
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        with app.test_client() as client:
            response = client.post(self.path, data=post_data)
            self.send_response(response.status_code)
            self.send_header('Content-type', response.content_type)
            self.end_headers()
            self.wfile.write(response.data)
