import os, time, threading, requests
TARGET = os.getenv("TARGET", "http://127.0.0.1:8000/")
BURST_REQUESTS = int(os.getenv("BURST_REQUESTS", "120"))
GOOD_TOTAL = int(os.getenv("GOOD_TOTAL", "60"))
GOOD_RATE = float(os.getenv("GOOD_RATE", "5"))

def spammer():
    ok = fail = 0
    t0 = time.perf_counter()
    for _ in range(BURST_REQUESTS):
        r = requests.get(TARGET)
        (ok := ok+1) if r.status_code < 400 else (fail := fail+1)
    dt = time.perf_counter() - t0
    print(f"[spam] ok={ok} fail={fail} success/s={ok/dt:.2f}")

def good_client():
    ok = fail = 0
    t0 = time.perf_counter()
    period = 1.0 / GOOD_RATE
    for _ in range(GOOD_TOTAL):
        s = time.perf_counter()
        r = requests.get(TARGET)
        (ok := ok+1) if r.status_code < 400 else (fail := fail+1)
        to_sleep = period - (time.perf_counter() - s)
        if to_sleep > 0: time.sleep(to_sleep)
    dt = time.perf_counter() - t0
    print(f"[good] ok={ok} fail={fail} success/s={ok/dt:.2f}")

if __name__ == "__main__":
    th1 = threading.Thread(target=spammer)
    th2 = threading.Thread(target=good_client)
    th1.start(); th2.start()
    th1.join(); th2.join()
