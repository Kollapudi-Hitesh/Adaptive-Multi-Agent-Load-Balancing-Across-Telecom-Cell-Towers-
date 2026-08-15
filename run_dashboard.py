import http.server
import socketserver
import webbrowser

PORT = 5500

server = socketserver.TCPServer(
    ("127.0.0.1", PORT),
    http.server.SimpleHTTPRequestHandler
)

url = f"http://127.0.0.1:{PORT}/midsem_dashboard.html"

print("Dashboard is running at:")
print(url)

webbrowser.open(url)

server.serve_forever()