#!/usr/bin/env python3
"""
Simple HTTP server to serve the RED ETF website locally
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

def serve_website():
    """Start a local HTTP server to serve the website"""
    
    # Set the port
    PORT = 8000
    
    # Change to the website directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Create a custom handler that serves .tsx files as JavaScript
    class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            # Add CORS headers for development
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()
        
        def guess_type(self, path):
            """Override MIME type guessing for better file serving"""
            mimetype, encoding = super().guess_type(path)
            
            # Handle TypeScript/JSX files
            if path.endswith(('.tsx', '.ts')):
                return 'application/javascript'
            
            # Handle JSON files
            if path.endswith('.json'):
                return 'application/json'
            
            return mimetype
    
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
