import networkx as nx
import matplotlib.pyplot as plt

G = nx.Graph()

# Important path
path = [
    "Site 196-3",
    "Site 196-1",
    "Site 182-1",
    "Site 172-1",
    "Site 159-1"
]

# Add path connections
for i in range(len(path) - 1):
    G.add_edge(path[i], path[i + 1])

# Draw graph
pos = nx.spring_layout(G, seed=1)

nx.draw(
    G,
    pos,
    with_labels=True,
    node_size=2500,
    node_color="orange",
    edge_color="red",
    font_size=9
)

plt.title("Optimized Network Path")
plt.show()