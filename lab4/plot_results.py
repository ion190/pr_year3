import json
import matplotlib.pyplot as plt
import os

INPUT = 'lab_spec_results.json'
OUT_PNG = 'quorum_vs_latency.png'

if not os.path.exists(INPUT):
    raise SystemExit(f"Input file not found: {INPUT}. Run the load test first.")

with open(INPUT) as f:
    results = json.load(f)

# Ensure sorted by quorum
results.sort(key=lambda r: r.get('quorum', 0))

qs = [r['quorum'] for r in results]
avgs = [r.get('avg_ms') for r in results]

plt.figure(figsize=(8,5))
plt.plot(qs, avgs, marker='o', label='avg')
plt.xlabel('write quorum (number of follower confirmations required)')
plt.ylabel('average latency (ms)')
plt.title('Quorum vs Average Write Latency')
plt.grid(True)
plt.xticks(qs)
plt.legend()
plt.tight_layout()
plt.savefig(OUT_PNG)
print(f'Saved {OUT_PNG}')
