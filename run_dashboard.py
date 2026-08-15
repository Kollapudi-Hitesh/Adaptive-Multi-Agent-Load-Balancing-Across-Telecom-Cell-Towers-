import http.server
import socketserver
import os
import json
import runpy


PORT = int(os.environ.get("PORT", 10000))


# ============================================================
# RUN MID-SEM PYTHON PROGRAM
# ============================================================

data = runpy.run_path("midsem_demo.py")


# ============================================================
# SEND RESULTS TO HTML
# ============================================================

results = {

    "dataset_records": len(data["df"]),

    "base_stations": data["number_of_sites"],

    "sectors": data["number_of_sectors"],

    "source": data["source"],

    "source_load": float(data["source_load"]),

    "target": data["target"],

    "target_load": float(data["target_load"]),

    "network_nodes": len(data["network"]),

    "network_edges": data["number_of_edges"],

    "dijkstra_path": data["dijkstra_path"],

    "dijkstra_cost": data["dijkstra_cost"],

    "dijkstra_nodes": data["dijkstra_visited"],

    "astar_path": data["astar_path"],

    "astar_cost": data["astar_cost"],

    "astar_nodes": data["astar_visited"],

    "low_threshold": float(data["low_threshold"]),

    "high_threshold": float(data["high_threshold"]),

    "node_loads": {
        node: float(info["load"])
        for node, info in data["network"].items()
    }

}


# ============================================================
# WEB SERVER
# ============================================================

class Handler(http.server.SimpleHTTPRequestHandler):


    def do_GET(self):

        # ----------------------------------------------------
        # MAIN PAGE
        # ----------------------------------------------------

        if self.path == "/":

            self.send_response(302)

            self.send_header(
                "Location",
                "/midsem_dashboard.html"
            )

            self.end_headers()

            return


        # ----------------------------------------------------
        # PYTHON RESULTS API
        # ----------------------------------------------------

        if self.path == "/api/results":

            response = json.dumps(
                results
            ).encode("utf-8")


            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.send_header(
                "Access-Control-Allow-Origin",
                "*"
            )

            self.send_header(
                "Content-Length",
                str(len(response))
            )

            self.end_headers()

            self.wfile.write(
                response
            )

            return


        # ----------------------------------------------------
        # NORMAL HTML / CSS / JS FILES
        # ----------------------------------------------------

        return super().do_GET()


# ============================================================
# START SERVER
# ============================================================

server = socketserver.TCPServer(
    ("0.0.0.0", PORT),
    Handler
)


print("============================================================")
print("       TELECOM NETWORK LOAD BALANCING DASHBOARD")
print("============================================================")

print("Server running on port:", PORT)

print("Dashboard:")
print("/midsem_dashboard.html")

print("API:")
print("/api/results")

print("============================================================")


server.serve_forever()
