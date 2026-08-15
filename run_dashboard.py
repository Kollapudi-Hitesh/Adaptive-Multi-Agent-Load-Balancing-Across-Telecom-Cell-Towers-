import http.server
import socketserver
import os

PORT = int(os.environ.get("PORT", 10000))

Handler = http.server.SimpleHTTPRequestHandler

server = socketserver.TCPServer(
    ("0.0.0.0", PORT),
    Handler
)

print("Dashboard is running")
print("Port:", PORT)

server.serve_forever()
