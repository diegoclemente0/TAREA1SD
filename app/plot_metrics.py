import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

csv_path = "data/metrics.csv"

output_dir = "outputs"
os.makedirs(output_dir, exist_ok=True)

df = pd.read_csv(csv_path)

df["latency_ms"].hist(by=df["served_from"], bins=50)
plt.suptitle("Distribución de latencias por origen")
plt.savefig(f"{output_dir}/latency_hist.png")
plt.close()

counts = df["served_from"].value_counts()
counts.plot(kind="bar", title="Hits vs Misses")
plt.ylabel("Requests")
plt.savefig(f"{output_dir}/hit_rate.png")
plt.close()

print(f"Gráficos guardados en la carpeta '{output_dir}'")
