HTTP server lab implemented in Python and Docker. It demonstrates:

- Single-threaded vs multithreaded request handling
- A per-path request counter with a deliberate race condition and a synchronized fix
- Per-IP rate limiting implemented in a thread-safe way
- A set of Dockerized test clients to benchmark and validate behavior

---

## Folder structure

```
├─ data/
│  └─ computer-networking-a-top-down-approach-8th-edition.pdf
├─ server_single.py
├─ server_threaded.py
├─ index.py          
├─ rate_limit_test.py
├─ Dockerfile        
└─ docker-compose.yml
```

### How the code works

- `server_single.py` uses `http.server.HTTPServer` + `SimpleHTTPRequestHandler`. It simulates ~1s of work per request and increments a global in-process counter per path. Single-threaded, so updates are safe.
- `server_threaded.py` uses `http.server.ThreadingHTTPServer` to serve requests concurrently. It has:
  - A request counter `HITS` keyed by the requested path.
  - A deliberate race mode `DEMO_RACE=true` that performs a read–modify–write with a tiny sleep to cause lost updates.
  - A synchronized mode that uses `threading.Lock()` to make increments atomic.
  - Per-IP rate limiting: a sliding 1-second window (`collections.deque`) guarded by a lock. Default limit is configured via `RATE_LIMIT` (requests/second/IP).
  - A custom directory listing that displays the per-item hit count.
- `index.py` fires N concurrent GETs to the server, measures total elapsed time, and prints successes. It reads `BASE_URL` and `CONCURRENCY` from the environment.
- `rate_limit_test.py` runs two clients:
  - A spammer intended to exceed the rate limit (make this concurrent to observe 429 responses).
  - A “good” client that sends requests just below the limit and should see near-zero failures.


## Quick start

```bash
docker compose build
```

Sanity-check from the host:

```bash
# Single-threaded server (port 8000)
docker compose up -d single
curl -I http://localhost:8000/

# Multithreaded server (port 8001)
docker compose up -d threaded
curl -I http://localhost:8001/
```

---

## Task 1 — Multithreaded HTTP server and comparison

Goal: compare handling time of N concurrent requests with single-threaded and multithreaded servers. The handlers simulate ~1s of work per request.

### Single-threaded baseline

```bash
docker compose up -d single
docker compose run --rm index_single
```


### Multithreaded server

```bash
docker compose up -d threaded
docker compose run --rm index_threaded
```


---

## Task 2 — Counter feature with race condition and fix

Goal: show a race condition in the per-path request counter, then remove it with synchronization.

### Show the race condition

Set `DEMO_RACE=true` and a high limit to avoid 429s:

```bash
docker compose stop threaded
# Ensure docker-compose.yml has:
# services.threaded.environment:
#   DEMO_RACE: "true"
#   RATE_LIMIT: "999"
#   SIM_DELAY_S: "1.0"
docker compose up -d --build threaded
docker compose run --rm   -e BASE_URL=http://threaded:8000   -e CONCURRENCY=20   index_threaded
```

Explanation:
- The naive increment does `read -> sleep -> write`, encouraging interleaving and lost updates.
- Open `http://localhost:8001/` and observe that the “Hits” count is lower than the number of requests.

### Fix the race

Switch to the locked increment:

```bash
docker compose stop threaded
# Change in docker-compose.yml:
#   DEMO_RACE: "false"
docker compose up -d --build threaded
docker compose run --rm   -e BASE_URL=http://threaded:8000   -e CONCURRENCY=20   index_threaded
```

Explanation:
- The increment is now guarded by a `threading.Lock()` so counts are accurate.
- Refresh `http://localhost:8001/`; hits should match requests sent.

---

## Task 3 — Rate limiting per IP (5 requests/second)

Goal: implement and demonstrate ~5 req/s per IP with a separate testing program.

### Configure the server with rate limit 5

```bash
docker compose stop threaded
# In docker-compose.yml:
# services.threaded.environment:
#   RATE_LIMIT: "5"
#   DEMO_RACE: "false"
#   SIM_DELAY_S: "1.0"
docker compose up -d --build threaded
```


### Run the rate-limit tester

```bash
docker compose run --rm rate_test
```

Explanation:
- The tester launches a spammer and a good client. Make the spammer concurrent (e.g., using a thread pool) so arrival rate exceeds 5 req/s. Under load, you should see 429 for the spammer while the good client stays near 5 successes per second.
- If your current spammer is sequential you may see ~1 req/s due to the simulated 1s work; increase spammer concurrency to exceed the limit.

---

## Commands reference

Build images:

```bash
docker compose build
```

Start servers:

```bash
docker compose up -d single
docker compose up -d threaded
```

Run benchmarks:

```bash
# single-threaded
docker compose run --rm -e BASE_URL=http://single:8000 -e CONCURRENCY=10 index_single

# multithreaded
docker compose run --rm -e BASE_URL=http://threaded:8000 -e CONCURRENCY=10 index_threaded
```

Toggle race demo:

```bash
docker compose stop threaded
# edit docker-compose.yml DEMO_RACE -> "true" or "false"
docker compose up -d --build threaded
```

Set rate limit:

```bash
docker compose stop threaded
# edit docker-compose.yml RATE_LIMIT -> "5" or "999"
docker compose up -d --build threaded
```

Run rate-limit test:

```bash
docker compose run --rm rate_test
```

Logs and diagnostics:

```bash
docker compose logs -f single
docker compose logs -f threaded
docker compose exec threaded env | grep -E 'RATE_LIMIT|SIM_DELAY_S|DEMO_RACE'
docker compose run --rm --entrypoint curl index_threaded -I http://threaded:8000/
```

Stop everything and remove resources:

```bash
docker compose down
```

---

## Expected results summary

- Single-threaded, 10 concurrent, ~1s simulated work: ~10 seconds total, 10 successes.
- Multithreaded, 10 concurrent, `RATE_LIMIT=999`: ~1–2 seconds total, 10 successes.
- Race demo on: “Hits” undercount vs requests when hammered concurrently.
- Race demo off: “Hits” match requests.
- Rate limiting at 5 req/s:
  - Spammer with high concurrency: many 429 responses, low success/s.
  - Good client at ~5/s: near-perfect success rate.

