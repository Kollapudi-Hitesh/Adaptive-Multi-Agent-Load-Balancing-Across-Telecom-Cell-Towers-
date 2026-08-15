import http.server
import socketserver
import os
import json
import runpy


PORT = int(os.environ.get("PORT", 10000))


# Run the existing mid-sem Python program
data = runpy.run_path("midsem_demo.py")


# Prepare results for HTML
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


class Handler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):

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
                "Content-Length",
                str(len(response))
            )

            self.end_headers()

            self.wfile.write(
                response
            )

            return


        return super().do_GET()


server = socketserver.TCPServer(
    ("0.0.0.0", PORT),
    Handler
)


print("Telecom dashboard server started.")

print("Port:", PORT)

server.serve_forever()
