import http.server
import socketserver
import os
import json
import runpy


# ============================================================
# SERVER PORT
# ============================================================

PORT = int(os.environ.get("PORT", 10000))


# ============================================================
# RUN YOUR EXISTING MID-SEM PYTHON PROGRAM
# ============================================================

data = runpy.run_path("midsem_demo.py")


df = data["df"]
network = data["network"]


# ============================================================
# CREATE TOWER INFORMATION FOR DASHBOARD
# ============================================================

tower_data = {}

for node in network:

    site = network[node]["site"]
    sector = network[node]["sector"]

    rows = df[
        (df["Base station"] == site) &
        (df["Sector"] == sector)
    ]

    if len(rows) > 0:

        rrc_users = float(
            rows["4G RRC users"].mean()
        )

        active_dl = float(
            rows["4G active users DL"].mean()
        )

        active_ul = float(
            rows["4G active users UL"].mean()
        )

    else:

        rrc_users = 0
        active_dl = 0
        active_ul = 0


    load = float(
        network[node]["load"]
    )


    if load <= data["low_threshold"]:

        status = "Low"

    elif load <= data["high_threshold"]:

        status = "Moderate"

    else:

        status = "High"


    tower_data[node] = {

        "site": site,

        "sector": sector,

        "users": round(rrc_users),

        "active_dl": round(active_dl, 2),

        "active_ul": round(active_ul, 2),

        "load": load,

        "status": status

    }


# ============================================================
# CREATE EDGE LIST
# ============================================================

edges = []

already_added = set()

for node in network:

    for neighbor in network[node]["neighbors"]:

        pair = tuple(
            sorted([node, neighbor])
        )

        if pair not in already_added:

            edges.append(
                [node, neighbor]
            )

            already_added.add(pair)


# ============================================================
# ALL RESULTS SENT TO HTML
# ============================================================

results = {

    "dataset_records":
        len(df),

    "base_stations":
        data["number_of_sites"],

    "sectors":
        data["number_of_sectors"],

    "network_nodes":
        len(network),

    "network_edges":
        data["number_of_edges"],

    "source":
        data["source"],

    "source_load":
        float(data["source_load"]),

    "target":
        data["target"],

    "target_load":
        float(data["target_load"]),

    "dijkstra_path":
        data["dijkstra_path"],

    "dijkstra_cost":
        data["dijkstra_cost"],

    "dijkstra_nodes":
        data["dijkstra_visited"],

    "astar_path":
        data["astar_path"],

    "astar_cost":
        data["astar_cost"],

    "astar_nodes":
        data["astar_visited"],

    "low_threshold":
        float(data["low_threshold"]),

    "high_threshold":
        float(data["high_threshold"]),

    "towers":
        tower_data,

    "edges":
        edges

}


# ============================================================
# WEB SERVER
# ============================================================

class Handler(
    http.server.SimpleHTTPRequestHandler
):


    def do_GET(self):

        # ----------------------------------------------------
        # OPEN DASHBOARD DIRECTLY
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
        # SEND PYTHON RESULTS
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


        return super().do_GET()


# ============================================================
# START SERVER
# ============================================================

server = socketserver.TCPServer(
    ("0.0.0.0", PORT),
    Handler
)


print(
    "============================================================"
)

print(
    "      TELECOM NETWORK LOAD BALANCING DASHBOARD"
)

print(
    "============================================================"
)

print(
    "Server running on port:",
    PORT
)

print(
    "Dashboard connected to midsem_demo.py"
)

print(
    "============================================================"
)


server.serve_forever()
