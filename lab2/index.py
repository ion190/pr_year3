import os, time, concurrent.futures, requests

BASE = os.getenv("BASE_URL", "http://127.0.0.1:8000")
CONCURRENCY = int(os.getenv("CONCURRENCY", "10"))

URLS = [
    f"{BASE}/",
    f"{BASE}/computer-networking-a-top-down-approach-8th-edition.pdf",
]

def hit(url):
    return requests.get(url, timeout=15).status_code

if __name__ == "__main__":
    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = [ex.submit(hit, URLS[i % len(URLS)]) for i in range(CONCURRENCY)]
        sts = [f.result() for f in futs]
    elapsed = time.perf_counter() - t0
    ok = sum(1 for s in sts if 200 <= s < 400)
    print(f"handled {CONCURRENCY} concurrent requests in {elapsed:.2f}s ({ok} successes)")
