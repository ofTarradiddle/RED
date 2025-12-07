#!/usr/bin/env python3
"""
Simple HTTP server to serve the RED ETF website locally
"""

import http.server
import socketserver
import os
import webbrowser
import json
from pathlib import Path
from datetime import datetime

def serve_website():
    """Start a local HTTP server to serve the website"""
    
    # Set the port
    PORT = 8080
    
    # Change to the website directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Newsletter subscriptions file
    NEWSLETTER_FILE = Path(__file__).parent / 'data' / 'newsletter_subscriptions.json'
    
    def ensure_data_dir():
        """Ensure the data directory exists."""
        NEWSLETTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    def load_subscriptions():
        """Load existing subscriptions from file."""
        ensure_data_dir()
        if NEWSLETTER_FILE.exists():
            try:
                with open(NEWSLETTER_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []
    
    def save_subscription(email):
        """Save a new subscription to the file."""
        subscriptions = load_subscriptions()
        
        # Check if email already exists
        if any(sub.get('email') == email for sub in subscriptions):
            return False
        
        # Add new subscription
        subscriptions.append({
            'email': email,
            'subscribed_at': datetime.now().isoformat(),
            'source': 'blog'
        })
        
        # Save to file
        ensure_data_dir()
        with open(NEWSLETTER_FILE, 'w') as f:
            json.dump(subscriptions, f, indent=2)
        
        return True
    
    # Create a custom handler that serves .tsx files as JavaScript
    class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            # Add CORS headers for development
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()
        
        def do_OPTIONS(self):
            """Handle OPTIONS requests for CORS"""
            self.send_response(200)
            self.end_headers()
        
        def do_POST(self):
            """Handle POST requests for newsletter subscription"""
            if self.path == '/api/newsletter-subscribe':
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                
                try:
                    data = json.loads(body) if body else {}
                    email = data.get('email', '').strip()
                    
                    if not email or '@' not in email:
                        self.send_response(400)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': 'Invalid email address'}).encode())
                        return
                    
                    if save_subscription(email):
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'message': 'Successfully subscribed', 'email': email}).encode())
                    else:
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'message': 'Already subscribed', 'email': email}).encode())
                except json.JSONDecodeError:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
            else:
                self.send_response(404)
                self.end_headers()
        
        def guess_type(self, path):
            """Override MIME type guessing for better file serving"""
            # Get parent result first to see format
            parent_result = super().guess_type(path)
            
            # Handle TypeScript/JSX files
            if path.endswith(('.tsx', '.ts')):
                if isinstance(parent_result, tuple):
                    return ('application/javascript',) + parent_result[1:]
                return 'application/javascript'
            
            # Handle JSON files
            if path.endswith('.json'):
                if isinstance(parent_result, tuple):
                    return ('application/json',) + parent_result[1:]
                return 'application/json'
            
            # Return parent result as-is
            return parent_result
    
    # Create the server
    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        print(f"🚀 RED ETF Website Server Starting...")
        print(f"📁 Serving from: {os.getcwd()}")
        print(f"🌐 Local URL: http://localhost:{PORT}")
        print(f"📄 Main page: http://localhost:{PORT}/index.html")
        print(f"📊 Test data: http://localhost:{PORT}/test-data.html")
        print(f"📝 Blog: http://localhost:{PORT}/blog/index.html")
        print(f"")
        print(f"Press Ctrl+C to stop the server")
        print(f"=" * 50)
        
        # Try to open the browser automatically
        try:
            webbrowser.open(f'http://localhost:{PORT}')
            print(f"🌐 Browser opened automatically")
        except:
            print(f"🌐 Please open http://localhost:{PORT} in your browser")
        
        # Start serving
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print(f"\n🛑 Server stopped by user")
            print(f"👋 Thanks for using RED ETF Website!")

if __name__ == "__main__":
    serve_website()
