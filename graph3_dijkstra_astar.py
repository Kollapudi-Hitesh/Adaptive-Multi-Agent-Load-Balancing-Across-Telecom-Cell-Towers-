import matplotlib.pyplot as plt

algorithms = ["Dijkstra", "A*"]

path_cost = [7, 7]
nodes_explored = [18, 18]

plt.figure(figsize=(8, 5))

plt.bar(algorithms, path_cost)

plt.title("Dijkstra vs A* - Path Cost")
plt.xlabel("Algorithm")
plt.ylabel("Path Cost")

plt.tight_layout()
plt.show()