import pandas as pd
import heapq

# ============================================================
# MID-SEMESTER DEMONSTRATION
# 50% IMPLEMENTATION
# ============================================================

print("\n============================================================")
print("      TELECOM NETWORK LOAD BALANCING - MID SEM DEMO")
print("============================================================")


# ============================================================
# STEP 1: LOAD CLEANED DATASET
# ============================================================

df = pd.read_csv("FAI_DATASET_CLEANED.csv")

print("\nSTEP 1: DATASET")
print("------------------------------------------------------------")
print("Dataset Shape:", df.shape)


# ============================================================
# STEP 2: BASIC NETWORK INFORMATION
# ============================================================

sectors = (
    df[["Base station", "Sector"]]
    .drop_duplicates()
    .reset_index(drop=True)
)

number_of_sites = df["Base station"].nunique()
number_of_sectors = len(sectors)

print("Number of Base Stations:", number_of_sites)
print("Number of Sectors:", number_of_sectors)


# ============================================================
# STEP 3: CALCULATE NORMALIZED LOAD VARIABLES
# ============================================================

load_columns = [
    "4G RB utilization",
    "4G RRC users",
    "4G active users DL",
    "4G active users UL",
    "4G data volume DL",
    "4G data volume UL"
]

for column in load_columns:

    minimum = df[column].min()
    maximum = df[column].max()

    if maximum == minimum:
        df[column + "_normalized"] = 0
    else:
        df[column + "_normalized"] = (
            (df[column] - minimum) /
            (maximum - minimum)
        )


# ============================================================
# STEP 4: CALCULATE LOAD SCORE
# ============================================================

df["Load Score"] = (
    0.50 * df["4G RB utilization_normalized"]
    + 0.15 * df["4G RRC users_normalized"]
    + 0.15 * df["4G active users DL_normalized"]
    + 0.05 * df["4G active users UL_normalized"]
    + 0.10 * df["4G data volume DL_normalized"]
    + 0.05 * df["4G data volume UL_normalized"]
)

print("\nSTEP 2: LOAD SCORE")
print("------------------------------------------------------------")
print("Load Score calculated successfully.")
print("Average Load Score:",
      round(df["Load Score"].mean(), 6))
print("Maximum Load Score:",
      round(df["Load Score"].max(), 6))


# ============================================================
# STEP 5: CALCULATE AVERAGE LOAD PER SECTOR
# ============================================================

sector_load = (
    df.groupby(
        ["Base station", "Sector"]
    )["Load Score"]
    .mean()
    .reset_index()
)


# ============================================================
# STEP 6: LOAD STATUS
# ============================================================

low_threshold = df["Load Score"].quantile(0.50)
high_threshold = df["Load Score"].quantile(0.75)

def get_status(load):

    if load <= low_threshold:
        return "Low"

    elif load <= high_threshold:
        return "Moderate"

    else:
        return "High"


sector_load["Load Status"] = (
    sector_load["Load Score"]
    .apply(get_status)
)

print("\nSTEP 3: LOAD STATUS")
print("------------------------------------------------------------")

print(
    sector_load["Load Status"]
    .value_counts()
)


# ============================================================
# STEP 7: FIND MOST CONGESTED SECTOR
# ============================================================

most_loaded = sector_load.sort_values(
    by="Load Score",
    ascending=False
).iloc[0]

source = (
    f"{most_loaded['Base station']}-"
    f"{most_loaded['Sector']}"
)

source_load = most_loaded["Load Score"]

print("\nSTEP 4: CONGESTION DETECTION")
print("------------------------------------------------------------")

print("Most Congested Sector:", source)
print("Congested Load:", round(source_load, 6))


# ============================================================
# STEP 8: FIND LOWEST-LOAD TARGET
# ============================================================

candidate_rows = sector_load[
    sector_load["Load Score"] < source_load
].sort_values(
    by="Load Score",
    ascending=True
)

target_row = candidate_rows.iloc[0]

target = (
    f"{target_row['Base station']}-"
    f"{target_row['Sector']}"
)

target_load = target_row["Load Score"]

print("Target Sector:", target)
print("Target Load:", round(target_load, 6))


# ============================================================
# STEP 9: CREATE NETWORK TOPOLOGY
# ============================================================

network = {}

for _, row in sectors.iterrows():

    site = row["Base station"]
    sector = row["Sector"]

    node = f"{site}-{sector}"

    network[node] = {
        "site": site,
        "sector": sector,
        "neighbors": {},
        "load": 0
    }


# ============================================================
# STEP 10: CONNECT SECTORS WITHIN SAME BASE STATION
# ============================================================

for site, group in sectors.groupby("Base station"):

    nodes = [
        f"{site}-{sector}"
        for sector in group["Sector"]
    ]

    for i in range(len(nodes)):

        for j in range(i + 1, len(nodes)):

            node_a = nodes[i]
            node_b = nodes[j]

            network[node_a]["neighbors"][node_b] = 1
            network[node_b]["neighbors"][node_a] = 1


# ============================================================
# STEP 11: CONNECT DIFFERENT BASE STATIONS
# ============================================================

sites = sorted(
    sectors["Base station"].unique(),
    key=lambda x: int(x.replace("Site ", ""))
)

for i in range(len(sites) - 1):

    site_a = sites[i]
    site_b = sites[i + 1]

    sectors_a = sectors[
        sectors["Base station"] == site_a
    ]["Sector"].tolist()

    sectors_b = sectors[
        sectors["Base station"] == site_b
    ]["Sector"].tolist()

    for sector in sectors_a:

        if sector in sectors_b:

            node_a = f"{site_a}-{sector}"
            node_b = f"{site_b}-{sector}"

            network[node_a]["neighbors"][node_b] = 2
            network[node_b]["neighbors"][node_a] = 2


# ============================================================
# STEP 12: ADD LOAD TO NETWORK NODES
# ============================================================

for _, row in sector_load.iterrows():

    node = (
        f"{row['Base station']}-"
        f"{row['Sector']}"
    )

    if node in network:
        network[node]["load"] = row["Load Score"]


# Count connections

number_of_edges = 0

for node in network:
    number_of_edges += len(
        network[node]["neighbors"]
    )

number_of_edges = number_of_edges // 2

print("\nSTEP 5: NETWORK TOPOLOGY")
print("------------------------------------------------------------")

print("Network Nodes:", len(network))
print("Network Connections:", number_of_edges)


# ============================================================
# STEP 13: DIJKSTRA ALGORITHM
# ============================================================

def dijkstra(graph, start, target):

    distances = {
        node: float("inf")
        for node in graph
    }

    previous = {
        node: None
        for node in graph
    }

    distances[start] = 0

    priority_queue = [
        (0, start)
    ]

    visited = set()

    while priority_queue:

        current_distance, current = heapq.heappop(
            priority_queue
        )

        if current in visited:
            continue

        visited.add(current)

        if current == target:
            break

        for neighbor, cost in graph[current]["neighbors"].items():

            new_distance = (
                current_distance + cost
            )

            if new_distance < distances[neighbor]:

                distances[neighbor] = new_distance
                previous[neighbor] = current

                heapq.heappush(
                    priority_queue,
                    (new_distance, neighbor)
                )

    path = []

    current = target

    while current is not None:

        path.append(current)
        current = previous[current]

    path.reverse()

    if not path or path[0] != start:
        return [], float("inf"), len(visited)

    return path, distances[target], len(visited)


# ============================================================
# STEP 14: A* ALGORITHM
# ============================================================

def heuristic(graph, node, target):

    return abs(
        graph[node]["load"]
        -
        graph[target]["load"]
    )


def astar(graph, start, target):

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

        f_score, current_g, current = heapq.heappop(
            open_list
        )

        if current in visited:
            continue

        visited.add(current)

        if current == target:
            break

        for neighbor, cost in graph[current]["neighbors"].items():

            tentative_g = (
                current_g + cost
            )

            if tentative_g < g_score[neighbor]:

                g_score[neighbor] = tentative_g

                h = heuristic(
                    graph,
                    neighbor,
                    target
                )

                new_f = (
                    tentative_g + h
                )

                previous[neighbor] = current

                heapq.heappush(
                    open_list,
                    (
                        new_f,
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

    if not path or path[0] != start:
        return [], float("inf"), len(visited)

    return path, g_score[target], len(visited)


# ============================================================
# STEP 15: RUN DIJKSTRA
# ============================================================

dijkstra_path, dijkstra_cost, dijkstra_visited = dijkstra(
    network,
    source,
    target
)


# ============================================================
# STEP 16: RUN A*
# ============================================================

astar_path, astar_cost, astar_visited = astar(
    network,
    source,
    target
)


# ============================================================
# STEP 17: DISPLAY DIJKSTRA RESULT
# ============================================================

print("\nSTEP 6: DIJKSTRA")
print("------------------------------------------------------------")

print("Source:", source)
print("Target:", target)

print("\nDijkstra Path:")

for node in dijkstra_path:
    print(" ->", node)

print("\nDijkstra Path Cost:", dijkstra_cost)
print("Nodes Explored:", dijkstra_visited)


# ============================================================
# STEP 18: DISPLAY A* RESULT
# ============================================================

print("\nSTEP 7: A*")
print("------------------------------------------------------------")

print("Source:", source)
print("Target:", target)

print("\nA* Path:")

for node in astar_path:
    print(" ->", node)

print("\nA* Path Cost:", astar_cost)
print("Nodes Explored:", astar_visited)


# ============================================================
# STEP 19: ALGORITHM COMPARISON
# ============================================================

print("\nSTEP 8: DIJKSTRA VS A*")
print("------------------------------------------------------------")

print(
    "Dijkstra Path Cost:",
    dijkstra_cost
)

print(
    "A* Path Cost:",
    astar_cost
)

print(
    "Dijkstra Nodes Explored:",
    dijkstra_visited
)

print(
    "A* Nodes Explored:",
    astar_visited
)

if astar_visited < dijkstra_visited:

    print(
        "\nA* explored fewer nodes than Dijkstra."
    )

elif astar_visited == dijkstra_visited:

    print(
        "\nBoth algorithms explored the same number of nodes."
    )

else:

    print(
        "\nDijkstra explored fewer nodes for this case."
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n============================================================")
print("             50% IMPLEMENTATION COMPLETED")
print("============================================================")

print("Dataset Records:", len(df))
print("Base Stations:", number_of_sites)
print("Sectors:", number_of_sectors)
print("Network Nodes:", len(network))
print("Network Connections:", number_of_edges)

print("\nCongested Sector:", source)
print("Congested Load:", round(source_load, 6))

print("Target Sector:", target)
print("Target Load:", round(target_load, 6))

print("\nDijkstra Cost:", dijkstra_cost)
print("A* Cost:", astar_cost)

print("\nCompleted Modules:")
print("1. Dataset preprocessing")
print("2. Missing value handling")
print("3. Data validation")
print("4. Load score calculation")
print("5. Congestion detection")
print("6. Network topology")
print("7. Dijkstra path optimization")
print("8. A* path optimization")

print("\nFuture Modules:")
print("1. D* dynamic replanning")
print("2. Q-Learning")
print("3. Multi-Agent coordination")
print("4. Hybrid optimization")

print("\n============================================================")
print("                  DEMONSTRATION COMPLETE")
print("============================================================")