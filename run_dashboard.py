from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import heapq
import os
import math


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================================
# GLOBAL DATA
# ============================================================

current_results = None


# ============================================================
# COLUMN DETECTION
# ============================================================

def find_column(df, possible_names):

    columns_lower = {
        str(c).lower().strip(): c
        for c in df.columns
    }

    for name in possible_names:

        if name.lower() in columns_lower:

            return columns_lower[name.lower()]

    # Partial matching

    for column in df.columns:

        column_lower = str(column).lower()

        for name in possible_names:

            if name.lower() in column_lower:

                return column

    return None


# ============================================================
# ANALYSE DATASET
# ============================================================

def analyse_dataset(file_path):

    df = pd.read_csv(file_path)


    # --------------------------------------------------------
    # DETECT IMPORTANT COLUMNS
    # --------------------------------------------------------

    base_station_col = find_column(
        df,
        [
            "Base station",
            "Base Station",
            "base_station",
            "site",
            "Site",
            "eNodeB",
            "Cell Site"
        ]
    )


    sector_col = find_column(
        df,
        [
            "Sector",
            "sector",
            "Cell",
            "cell",
            "Sector ID"
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
            "users",
            "Users",
            "User Count",
            "Number of Users"
        ]
    )


    dl_col = find_column(
        df,
        [
            "4G active users DL",
            "active users DL",
            "Active Users DL"
        ]
    )


    ul_col = find_column(
        df,
        [
            "4G active users UL",
            "active users UL",
            "Active Users UL"
        ]
    )


    data_dl_col = find_column(
        df,
        [
            "4G data volume DL",
            "data volume DL",
            "Data Volume DL"
        ]
    )


    data_ul_col = find_column(
        df,
        [
            "4G data volume UL",
            "data volume UL",
            "Data Volume UL"
        ]
    )


    # --------------------------------------------------------
    # BASE STATION / SECTOR FALLBACK
    # --------------------------------------------------------

    if base_station_col is None:

        # Try first text column

        text_columns = df.select_dtypes(
            include=["object"]
        ).columns.tolist()

        if text_columns:

            base_station_col = text_columns[0]

        else:

            df["Base station"] = [
                f"Site {i+1}"
                for i in range(len(df))
            ]

            base_station_col = "Base station"


    if sector_col is None:

        df["Sector"] = 1

        sector_col = "Sector"


    # --------------------------------------------------------
    # CONVERT NUMERIC COLUMNS
    # --------------------------------------------------------

    numeric_columns = [
        rb_col,
        rrc_col,
        dl_col,
        ul_col,
        data_dl_col,
        data_ul_col
    ]


    for column in numeric_columns:

        if column is not None:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

            df[column] = df[column].fillna(0)


    # --------------------------------------------------------
    # USER COLUMN
    # --------------------------------------------------------

    if rrc_col is None:

        if dl_col is not None:

            df["_users"] = df[dl_col]

        elif ul_col is not None:

            df["_users"] = df[ul_col]

        else:

            # Last fallback

            df["_users"] = 1

        rrc_col = "_users"


    # --------------------------------------------------------
    # LOAD COMPONENTS
    # --------------------------------------------------------

    load_components = []


    def normalize(column):

        minimum = df[column].min()

        maximum = df[column].max()

        if maximum == minimum:

            return pd.Series(
                [0] * len(df),
                index=df.index
            )

        return (
            (df[column] - minimum)
            /
            (maximum - minimum)
        )


    if rb_col is not None:

        load_components.append(
            (
                normalize(rb_col),
                0.50
            )
        )


    if rrc_col is not None:

        load_components.append(
            (
                normalize(rrc_col),
                0.15
            )
        )


    if dl_col is not None:

        load_components.append(
            (
                normalize(dl_col),
                0.15
            )
        )


    if ul_col is not None:

        load_components.append(
            (
                normalize(ul_col),
                0.05
            )
        )


    if data_dl_col is not None:

        load_components.append(
            (
                normalize(data_dl_col),
                0.10
            )
        )


    if data_ul_col is not None:

        load_components.append(
            (
                normalize(data_ul_col),
                0.05
            )
        )


    # --------------------------------------------------------
    # FALLBACK LOAD
    # --------------------------------------------------------

    if not load_components:

        load_components.append(
            (
                normalize(rrc_col),
                1.0
            )
        )


    # --------------------------------------------------------
    # LOAD SCORE
    # --------------------------------------------------------

    df["Load Score"] = 0.0


    total_weight = sum(
        weight
        for _, weight in load_components
    )


    for values, weight in load_components:

        df["Load Score"] += (
            values *
            weight /
            total_weight
        )


    # --------------------------------------------------------
    # SECTOR INFORMATION
    # --------------------------------------------------------

    sector_load = (

        df.groupby(
            [
                base_station_col,
                sector_col
            ]
        )

        .agg(

            Load_Score=(
                "Load Score",
                "mean"
            ),

            Users=(
                rrc_col,
                "mean"
            )

        )

        .reset_index()

    )


    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    low_threshold = (
        sector_load["Load_Score"]
        .quantile(0.50)
    )


    high_threshold = (
        sector_load["Load_Score"]
        .quantile(0.75)
    )


    def status(load):

        if load <= low_threshold:

            return "Low"

        elif load <= high_threshold:

            return "Moderate"

        return "High"


    sector_load["Status"] = (
        sector_load["Load_Score"]
        .apply(status)
    )


    # --------------------------------------------------------
    # CREATE NETWORK
    # --------------------------------------------------------

    network = {}


    for _, row in sector_load.iterrows():

        node = (
            f"{row[base_station_col]}-"
            f"{row[sector_col]}"
        )


        network[node] = {

            "site":
                str(row[base_station_col]),

            "sector":
                str(row[sector_col]),

            "load":
                float(row["Load_Score"]),

            "users":
                float(row["Users"]),

            "neighbors": {}

        }


    # --------------------------------------------------------
    # CONNECT SECTORS OF SAME SITE
    # --------------------------------------------------------

    sites = (
        sector_load[
            base_station_col
        ]
        .astype(str)
        .unique()
        .tolist()
    )


    for site in sites:

        site_nodes = [

            node

            for node in network

            if network[node]["site"] == site

        ]


        for i in range(len(site_nodes)):

            for j in range(i + 1, len(site_nodes)):

                a = site_nodes[i]

                b = site_nodes[j]

                network[a]["neighbors"][b] = 1

                network[b]["neighbors"][a] = 1


    # --------------------------------------------------------
    # CONNECT DIFFERENT SITES
    # --------------------------------------------------------

    sites_sorted = sites


    for i in range(
        len(sites_sorted) - 1
    ):

        site_a = sites_sorted[i]

        site_b = sites_sorted[i + 1]


        sectors_a = [

            network[node]["sector"]

            for node in network

            if network[node]["site"] == site_a

        ]


        sectors_b = [

            network[node]["sector"]

            for node in network

            if network[node]["site"] == site_b

        ]


        for sector in sectors_a:

            if sector in sectors_b:

                node_a = (
                    f"{site_a}-{sector}"
                )

                node_b = (
                    f"{site_b}-{sector}"
                )


                network[node_a]["neighbors"][
                    node_b
                ] = 2


                network[node_b]["neighbors"][
                    node_a
                ] = 2


    # --------------------------------------------------------
    # EDGE LIST
    # --------------------------------------------------------

    edges = []

    seen = set()


    for node in network:

        for neighbor in network[node]["neighbors"]:

            pair = tuple(
                sorted(
                    [node, neighbor]
                )
            )


            if pair not in seen:

                edges.append(
                    list(pair)
                )

                seen.add(pair)


    # --------------------------------------------------------
    # FIND SOURCE
    # --------------------------------------------------------

    source = max(
        network,
        key=lambda x:
        network[x]["load"]
    )


    source_load = (
        network[source]["load"]
    )


    # --------------------------------------------------------
    # FIND TARGET
    # --------------------------------------------------------

    candidates = [

        node

        for node in network

        if node != source

    ]


    target = min(

        candidates,

        key=lambda x:
        network[x]["load"]

    )


    target_load = (
        network[target]["load"]
    )


    # --------------------------------------------------------
    # DIJKSTRA
    # --------------------------------------------------------

    def dijkstra(
        graph,
        start,
        target
    ):

        distances = {
            node: float("inf")
            for node in graph
        }


        previous = {
            node: None
            for node in graph
        }


        distances[start] = 0


        queue = [
            (0, start)
        ]


        visited = set()


        while queue:

            distance, current = (
                heapq.heappop(queue)
            )


            if current in visited:

                continue


            visited.add(current)


            if current == target:

                break


            for neighbor, cost in (
                graph[current]["neighbors"]
                .items()
            ):

                new_distance = (
                    distance + cost
                )


                if (
                    new_distance
                    <
                    distances[neighbor]
                ):

                    distances[neighbor] = (
                        new_distance
                    )

                    previous[neighbor] = (
                        current
                    )


                    heapq.heappush(
                        queue,
                        (
                            new_distance,
                            neighbor
                        )
                    )


        path = []

        current = target


        while current is not None:

            path.append(current)

            current = previous[current]


        path.reverse()


        if (
            not path
            or path[0] != start
        ):

            return [], float("inf"), len(visited)


        return (
            path,
            distances[target],
            len(visited)
        )


    # --------------------------------------------------------
    # A*
    # --------------------------------------------------------

    def heuristic(
        graph,
        node,
        target
    ):

        return abs(

            graph[node]["load"]
            -
            graph[target]["load"]

        )


    def astar(
        graph,
        start,
        target
    ):

        open_list = []


        g_score = {
            node: float("inf")
            for node in graph
        }


        previous = {
            node: None
            for node in graph
        }


        g_score[start] = 0


        h = heuristic(
            graph,
            start,
            target
        )


        heapq.heappush(
            open_list,
            (h, 0, start)
        )


        visited = set()


        while open_list:

            f_score, current_g, current = (
                heapq.heappop(open_list)
            )


            if current in visited:

                continue


            visited.add(current)


            if current == target:

                break


            for neighbor, cost in (
                graph[current]["neighbors"]
                .items()
            ):

                tentative_g = (
                    current_g + cost
                )


                if (
                    tentative_g
                    <
                    g_score[neighbor]
                ):

                    g_score[neighbor] = (
                        tentative_g
                    )


                    h = heuristic(
                        graph,
                        neighbor,
                        target
                    )


                    previous[neighbor] = (
                        current
                    )


                    heapq.heappush(
                        open_list,
                        (
                            tentative_g + h,
                            tentative_g,
                            neighbor
                        )
                    )


        path = []

        current = target


        while current is not None:

            path.append(current)

            current = previous[current]


        path.reverse()


        if (
            not path
            or path[0] != start
        ):

            return [], float("inf"), len(visited)


        return (
            path,
            g_score[target],
            len(visited)
        )


    dijkstra_path, dijkstra_cost, dijkstra_nodes = (
        dijkstra(
            network,
            source,
            target
        )
    )


    astar_path, astar_cost, astar_nodes = (
        astar(
            network,
            source,
            target
        )
    )


    # --------------------------------------------------------
    # TOWER DATA
    # --------------------------------------------------------

    towers = {}


    for node in network:

        towers[node] = {

            "site":
                network[node]["site"],

            "sector":
                network[node]["sector"],

            "users":
                round(
                    network[node]["users"]
                ),

            "load":
                network[node]["load"],

            "status":
                status(
                    network[node]["load"]
                )

        }


    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    return {

        "records":
            len(df),

        "columns":
            list(df.columns),

        "base_stations":
            len(sites),

        "sectors":
            len(network),

        "edges":
            len(edges),

        "source":
            source,

        "source_load":
            source_load,

        "target":
            target,

        "target_load":
            target_load,

        "towers":
            towers,

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
            astar_nodes,

        "low_threshold":
            low_threshold,

        "high_threshold":
            high_threshold

    }


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

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
def upload():

    global current_results


    if "dataset" not in request.files:

        return jsonify({
            "error":
                "Please select a CSV dataset."
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
                "Only CSV files are supported."
        }), 400


    path = os.path.join(
        UPLOAD_FOLDER,
        "current_dataset.csv"
    )


    file.save(path)


    try:

        current_results = (
            analyse_dataset(path)
        )


        return jsonify(
            current_results
        )


    except Exception as e:

        return jsonify({
            "error":
                str(e)
        }), 500


# ============================================================
# GET RESULTS
# ============================================================

@app.route("/api/results")
def api_results():

    if current_results is None:

        return jsonify({
            "error":
                "Upload a dataset first."
        }), 404


    return jsonify(
        current_results
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )


    print(
        "=============================================="
    )

    print(
        " TELECOM LOAD BALANCING DASHBOARD"
    )

    print(
        "=============================================="
    )

    print(
        "Running on port:",
        port
    )


    app.run(
        host="0.0.0.0",
        port=port
    )
