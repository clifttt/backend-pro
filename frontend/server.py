#!/usr/bin/env python3
"""No-cache HTTP server for frontend development."""
import http.server
import sys

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # suppress noisy logs

port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
print(f"Frontend server running at http://localhost:{port} (no-cache mode)")
http.server.test(HandlerClass=NoCacheHandler, port=port, bind="")
