import requests
import time
import random
import statistics
from concurrent.futures import ThreadPoolExecutor

LEADER = 'http://localhost:8000'
NUM_WRITES = 100
NUM_WORKERS = 10
NUM_KEYS = 10

def do_write(i, quorum):
    key = f'k-{random.randrange(NUM_KEYS)}'
    value = f'v-{i}-{random.random()}'
    start = time.time()
    try:
        r = requests.post(f'{LEADER}/put', json={'key': key, 'value': value, 'quorum': quorum}, timeout=30)
        ok = r.status_code == 200
    except Exception:
        ok = False
    latency = (time.time() - start) * 1000.0
    return latency, ok

def run_for_quorum(quorum):
    latencies = []
    successes = 0
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as ex:
        futures = [ex.submit(do_write, i, quorum) for i in range(NUM_WRITES)]
        for f in futures:
            try:
                lat, ok = f.result()
                latencies.append(lat)
                if ok:
                    successes += 1
            except Exception as e:
                print('write failed', e)
    return {'quorum': quorum, 'avg_ms': statistics.mean(latencies), 'successes': successes}

if __name__ == '__main__':
    import json
    results = []
    for q in range(1, 6):
        print('running for quorum', q)
        res = run_for_quorum(q)
        print(res)
        results.append(res)
    with open('lab_spec_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print('done')
