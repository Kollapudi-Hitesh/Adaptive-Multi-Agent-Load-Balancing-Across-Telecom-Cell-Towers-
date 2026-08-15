import matplotlib.pyplot as plt

status = ["Low", "Moderate", "High"]
count = [25, 30, 18]

plt.bar(status, count)

plt.title("Network Load Status Distribution")
plt.xlabel("Load Status")
plt.ylabel("Number of Sectors")

plt.show()