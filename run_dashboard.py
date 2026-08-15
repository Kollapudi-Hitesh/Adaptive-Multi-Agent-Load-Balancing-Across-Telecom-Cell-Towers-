from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import heapq
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

RESULTS = None


# ============================================================
# FIND COLUMN
# ============================================================

def find_column(df, names):

    for name in names:

        for col in df.columns:

            if str(col).strip().lower() == name.lower():
                return col

    # Partial match
    for name in names:

        for col in df.columns:

            if name.lower() in str(col).lower():
                return col

    return None


# ============================================================
# NORMALIZE COLUMN
# ============================================================

def normalize(series):

    series = pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(0)

    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        return pd.Series(
            [0.0] * len(series),
            index=series.index
        )

    return (series - minimum) / (maximum - minimum)


# ============================================================
# ANALYSE DATASET
# ============================================================

def analyse_dataset(file_path):

    df = pd.read_csv(file_path)

    # --------------------------------------------------------
    # FIND COLUMNS
    # --------------------------------------------------------

    site_col = find_column(
        df,
        [
            "Base station",
            "Base Station",
            "site",
            "Site",
            "Cell Site"
        ]
    )

    sector_col = find_column(
        df,
        [
            "Sector",
            "sector",
            "Cell",
            "cell"
        ]
    )

    rb_col = find_column(
        df,
        [
            "4G RB utilization",
            "RB utilization",
            "RB Utilization",
            "PRB utilization",
            "PRB Utilization"
        ]
    )

    rrc_col = find_column(
        df,
        [
            "4G RRC users",
            "RRC users",
            "RRC Users",
            "Users",
            "users"
        ]
    )

    dl_users_col = find_column(
        df,
        [
            "4G active users DL",
            "active users DL",
            "Active Users DL"
        ]
    )

    ul_users_col = find_column(
        df,
        [
            "4G active users UL",
            "active users UL",
            "Active Users UL"
        ]
    )

    dl_data_col = find_column(
        df,
        [
            "4G data volume DL",
            "data volume DL",
            "Data Volume DL"
        ]
    )

    ul_data_col = find_column(
        df,
        [
            "4G data volume UL",
            "data volume UL",
            "Data Volume UL"
        ]
    )

    # --------------------------------------------------------
    # SITE FALLBACK
    # --------------------------------------------------------

    if site_col is None:

        df["Site"] = [
            "Site " + str(i + 1)
            for i in range(len(df))
        ]

        site_col = "Site"

    # --------------------------------------------------------
    # SECTOR FALLBACK
    # --------------------------------------------------------

    if sector_col is None:

        df["Sector"] = 1

        sector_col = "Sector"

    # --------------------------------------------------------
    # USER FALLBACK
    # --------------------------------------------------------

    if rrc_col is None:

        if dl_users_col is not None:

            df["_users"] = pd.to_numeric(
                df[dl_users_col],
                errors="coerce"
            ).fillna(0)

        elif ul_users_col is not None:

            df["_users"] = pd.to_numeric(
                df[ul_users_col],
                errors="coerce"
            ).fillna(0)

        else:

            df["_users"] = 1

        rrc_col = "_users"

    # --------------------------------------------------------
    # CONVERT NUMERIC DATA
    # --------------------------------------------------------

    numeric_cols = [
        rb_col,
        rrc_col,
        dl_users_col,
        ul_users_col,
        dl_data_col,
        ul_data_col
    ]

    for col in numeric_cols:

        if col is not None:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0)

    # --------------------------------------------------------
    # LOAD SCORE
    # --------------------------------------------------------

    df["Load Score"] = 0.0

    weights = []

    if rb_col is not None:
        weights.append(
            (normalize(df[rb_col]), 0.50)
        )

    if rrc_col is not None:
        weights.append(
            (normalize(df[rrc_col]), 0.20)
        )

    if dl_users_col is not None:
        weights.append(
            (normalize(df[dl_users_col]), 0.10)
        )

    if ul_users_col is not None:
        weights.append(
            (normalize(df[ul_users_col]), 0.05)
        )

    if dl_data_col is not None:
        weights.append(
            (normalize(df[dl_data_col]), 0.10)
        )

    if ul_data_col is not None:
        weights.append(
            (normalize(df[ul_data_col]), 0.05)
        )

    if not weights:

        weights.append(
            (normalize(df[rrc_col]), 1.0)
        )

    total_weight = sum(
        weight for values, weight in weights
    )

    for values, weight in weights:

        df["Load Score"] += (
            values * weight / total_weight
        )

    # --------------------------------------------------------
    # GROUP BY SITE + SECTOR
    # --------------------------------------------------------

    grouped = (
        df.groupby(
            [site_col, sector_col]
        )
        .agg(
            Load_Score=("Load Score", "mean"),
            Users=(rrc_col, "mean")
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # LOAD STATUS
    # --------------------------------------------------------

    low_limit = grouped["Load_Score"].quantile(0.50)
    high_limit = grouped["Load_Score"].quantile(0.75)

    def get_status(value):

        if value <= low_limit:
            return "Low"

        if value <= high_limit:
            return "Moderate"

        return "High"

    grouped["Status"] = grouped[
        "Load_Score"
    ].apply(get_status)

    # --------------------------------------------------------
    # CREATE NETWORK NODES
    # --------------------------------------------------------

    towers = {}

    for _, row in grouped.iterrows():

        site = str(row[site_col])
        sector = str(row[sector_col])

        node = site + "-" + sector

        towers[node] = {

            "site": site,

            "sector": sector,

            "users": int(
                round(row["Users"])
            ),

            "load": float(
                row["Load_Score"]
            ),

            "status": row["Status"],

            "neighbors": {}

        }

    # --------------------------------------------------------
    # CREATE EDGES
    #
    # Simple telecom topology:
    # Each sector connects to nearby sectors.
    # --------------------------------------------------------

    nodes = list(towers.keys())

    for i in range(len(nodes) - 1):

        a = nodes[i]
        b = nodes[i + 1]

        towers[a]["neighbors"][b] = 1
        towers[b]["neighbors"][a] = 1

    # Add a few additional connections

    for i in range(0, len(nodes) - 3, 3):

        a = nodes[i]
        b = nodes[i + 3]

        towers[a]["neighbors"][b] = 2
        towers[b]["neighbors"][a] = 2

    # --------------------------------------------------------
    # EDGE LIST
    # --------------------------------------------------------

    edges = []
    seen = set()

    for node in towers:

        for neighbour in towers[node]["neighbors"]:

            pair = tuple(
                sorted([node, neighbour])
            )

            if pair not in seen:

                edges.append(
                    [pair[0], pair[1]]
                )

                seen.add(pair)

    # --------------------------------------------------------
    # SOURCE = MOST CONGESTED
    # --------------------------------------------------------

    source = max(
        towers,
        key=lambda node:
        towers[node]["load"]
    )

    # --------------------------------------------------------
    # TARGET = LOWEST LOAD
    # --------------------------------------------------------

    possible_targets = [
        node
        for node in towers
        if node != source
    ]

    target = min(
        possible_targets,
        key=lambda node:
        towers[node]["load"]
    )

    # --------------------------------------------------------
    # DIJKSTRA
    # --------------------------------------------------------

    def dijkstra(start, goal):

        distance = {
            node: float("inf")
            for node in towers
        }

        previous = {
            node: None
            for node in towers
        }

        distance[start] = 0

        queue = [
            (0, start)
        ]

        visited = set()

        while queue:

            current_distance, current = heapq.heappop(
                queue
            )

            if current in visited:
                continue

            visited.add(current)

            if current == goal:
                break

            for neighbour, cost in towers[
                current
            ]["neighbors"].items():

                new_distance = (
                    current_distance + cost
                )

                if new_distance < distance[neighbour]:

                    distance[neighbour] = new_distance

                    previous[neighbour] = current

                    heapq.heappush(
                        queue,
                        (
                            new_distance,
                            neighbour
                        )
                    )

        path = []

        current = goal

        while current is not None:

            path.append(current)

            current = previous[current]

        path.reverse()

        if path[0] != start:

            return [], 0, len(visited)

        return (
            path,
            distance[goal],
            len(visited)
        )

    # --------------------------------------------------------
    # A* HEURISTIC
    # --------------------------------------------------------

    def heuristic(node, goal):

        return abs(
            towers[node]["load"]
            -
            towers[goal]["load"]
        )

    # --------------------------------------------------------
    # A*
    # --------------------------------------------------------

    def astar(start, goal):

        g_score = {
            node: float("inf")
            for node in towers
        }

        previous = {
            node: None
            for node in towers
        }

        g_score[start] = 0

        queue = [
            (
                heuristic(start, goal),
                0,
                start
            )
        ]

        visited = set()

        while queue:

            f_score, current_g, current = heapq.heappop(
                queue
            )

            if current in visited:
                continue

            visited.add(current)

            if current == goal:
                break

            for neighbour, cost in towers[
                current
            ]["neighbors"].items():

                new_g = current_g + cost

                if new_g < g_score[neighbour]:

                    g_score[neighbour] = new_g

                    previous[neighbour] = current

                    new_f = (
                        new_g
                        +
                        heuristic(
                            neighbour,
                            goal
                        )
                    )

                    heapq.heappush(
                        queue,
                        (
                            new_f,
                            new_g,
                            neighbour
                        )
                    )

        path = []

        current = goal

        while current is not None:

            path.append(current)

            current = previous[current]

        path.reverse()

        if path[0] != start:

            return [], 0, len(visited)

        return (
            path,
            g_score[goal],
            len(visited)
        )

    # --------------------------------------------------------
    # RUN ALGORITHMS
    # --------------------------------------------------------

    dijkstra_path, dijkstra_cost, dijkstra_nodes = (
        dijkstra(
            source,
            target
        )
    )

    astar_path, astar_cost, astar_nodes = (
        astar(
            source,
            target
        )
    )

    # --------------------------------------------------------
    # REMOVE NEIGHBOURS FROM JSON OUTPUT
    # --------------------------------------------------------

    tower_output = {}

    for node in towers:

        tower_output[node] = {

            "site":
                towers[node]["site"],

            "sector":
                towers[node]["sector"],

            "users":
                towers[node]["users"],

            "load":
                towers[node]["load"],

            "status":
                towers[node]["status"]

        }

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    return {

        "records":
            int(len(df)),

        "base_stations":
            int(
                grouped[site_col]
                .nunique()
            ),

        "sectors":
            int(len(towers)),

        "edges":
            int(len(edges)),

        "source":
            source,

        "source_load":
            float(
                towers[source]["load"]
            ),

        "target":
            target,

        "target_load":
            float(
                towers[target]["load"]
            ),

        "towers":
            tower_output,

        "edges_list":
            edges,

        "dijkstra_path":
            dijkstra_path,

        "dijkstra_cost":
            dijkstra_cost,

        "dijkstra_nodes":
            dijkstra_nodes,

        "astar_path":
            astar_path,

        "astar_cost":
            astar_cost,

        "astar_nodes":
            astar_nodes

    }


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
def dashboard():

    return send_from_directory(
        ".",
        "midsem_dashboard.html"
    )


# ============================================================
# UPLOAD DATASET
# ============================================================

@app.route(
    "/upload",
    methods=["POST"]
)
def upload_dataset():

    global RESULTS

    if "dataset" not in request.files:

        return jsonify({
            "error":
                "No dataset uploaded."
        }), 400

    file = request.files["dataset"]

    if file.filename == "":

        return jsonify({
            "error":
                "No file selected."
        }), 400

    if not file.filename.lower().endswith(".csv"):

        return jsonify({
            "error":
                "Please upload a CSV file."
        }), 400

    file_path = os.path.join(
        UPLOAD_FOLDER,
        "dataset.csv"
    )

    file.save(file_path)

    try:

        RESULTS = analyse_dataset(
            file_path
        )

        return jsonify(
            RESULTS
        )

    except Exception as error:

        print(
            "DATASET ERROR:",
            error
        )

        return jsonify({
            "error":
                str(error)
        }), 500


# ============================================================
# GET RESULTS
# ============================================================

@app.route("/api/results")
def get_results():

    if RESULTS is None:

        return jsonify({
            "error":
                "No dataset has been uploaded yet."
        }), 404

    return jsonify(
        RESULTS
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "running"
    })


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    print(
        "Telecom Load Balancing Dashboard"
    )

    print(
        "Server running on port:",
        port
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
