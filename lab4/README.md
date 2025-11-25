# Single-leader KV store

## Overview
This project implements a minimal **single-leader key-value store** with **semi-synchronous replication** to 5 followers. The leader accepts writes, applies them locally, and concurrently replicates to followers via HTTP JSON endpoints. The leader waits for a configurable number of follower acknowledgements (the *write quorum*) before reporting success.

This repo is designed for experiments: measuring write latency vs write quorum and observing replication completeness.


---

## Environment variables (configurable)
- `ROLE` — `leader` or `follower` (set by compose)
- `PORT` — container listening port
- `FOLLOWER_COUNT` — number of followers known to leader (default 5)
- `WRITE_QUORUM` — number of follower confirmations leader waits for (default 3)
- `MIN_DELAY_MS` — min artificial per-follower delay (ms) before replicate request
- `MAX_DELAY_MS` — max artificial per-follower delay (ms)
- `FOLLOWER_BASE_URL` — (not heavily used in example) base prefix for follower services
- `FOLLOWER_ID` — follower index for follower containers

These are configured in `docker-compose.yml` when you redeploy leader manually.

---

## How to run (basic)

Build & start everything:


   ```bash
   docker-compose up -d --build
   ```


---

## Commands & workflows (full detail)



### Integration test (simple correctness)
From host (requires Python `requests` installed):

```bash
python3 integration_test.py
```
This posts a `/put` with `quorum: 5` and verifies all followers eventually contain the key.

### Load test (latency measurement)

```bash
python3 load_test.py
```
- This performs `NUM_WRITES` concurrent writes across `NUM_WORKERS`.
- It overrides leader quorum per request by sending `{"quorum": X}` with each `/put`.
- Output: `results_q{quorum}.json` or `all_results.json` containing average latency, p50, and success counts.


### Plot results
After experiments:

```bash
python3 plot_results.py
```

### Data mismatches

```bash
python3 compare_replicas.py
```

---

## What the leader does (implementation summary)
- On `POST /put {key,value, optional quorum}`:
  1. **Apply locally** in the in-memory store (`store.put`).
  2. Launch asynchronous replication requests to all followers **concurrently**.
  3. Wait until `write_quorum` follower responses come back (or timeout). The default `WRITE_QUORUM` is read from env; per-request `quorum` can override it.
  4. If `confirmations >= write_quorum`, return success to client; otherwise return 500/failure.
  5. Remaining in-flight replication tasks are cancelled in this simple implementation (so some followers may not be updated immediately).

- On follower `/replicate`:
  - Apply the write to local store and return success.

---

## How latency is measured in load tests
- The client measures **end-to-end latency**: time from sending `POST /put` to receiving the leader's response (including local write + waiting for `quorum` acks).
- Recorded metrics: average (mean), median (p50), and success count.
- For more detailed insight, extend `load_test.py` to also compute p95 and p99 latencies.

---

## Expected experimental results — short summary
- **As `write_quorum` increases**, average write latency increases. Reason: the leader must wait for more follower confirmations; in the presence of per-follower random delays, waiting for the `k`-th fastest follower takes longer as `k` increases (order-statistic effect).
- **Success rate** can drop if followers are slow/unreachable causing the leader to time out before reaching quorum.
- **Replica divergence immediately after experiments** is expected since we cancel remaining replication tasks after quorum; some followers might never have received some writes at the time the leader returned success.

---

## Theory / Concepts (detailed)

### Single-leader replication
- **Leader**: single node that accepts all client writes and serializes them.
- **Follower**: replica that receives replicated writes from the leader. Usually serves reads (sometimes stale) but does not accept writes.

### Replication modes
- **Synchronous replication**: leader blocks until replicas acknowledge the write; strong durability and consistency but high write latency.
- **Asynchronous replication**: leader returns immediately after local commit and replication happens in background; low latency but risk of data loss if leader fails before replication completes.
- **Semi-synchronous replication**: leader waits for some **quorum** of replicas (≥1 and ≤N) then returns success. Balances durability and latency.

### Quorum
- A **write quorum** is how many follower confirmations are required before reporting success.
- Larger quorum → more durable, but higher latency.
- Typical trade-offs: performance vs durability/availability.

### Consistency models
- **Linearizability**: each operation appears to take effect at a single point in time — strongest, intuitive consistency for reads/writes.
  - Single-leader with local apply + waiting for quorum can provide linearizability for operations that go through leader, if reads are also routed to leader (or if read quorums are used properly).
- **Eventual consistency**: replicas will converge eventually but reads may be stale.
- **Read-after-write**: important to know whether a read right after a write will reflect that write (depends on read routing and replication guarantees).

### Durability and failure behavior
- If leader crashes before replication and followers did not persist the write, the data may be lost.
- Robust systems use a **write-ahead log (WAL)**: leader writes to persistent log before acknowledging; followers also persist and track log positions to catch up.
- For correct leader failover, a consensus algorithm (Raft/Paxos) is used to elect a new leader and ensure committed entries are preserved.

### Why latency increases with quorum (intuitively)
- Imagine replication round-trip times to each follower are independent random variables. Time to get `k` successful responses is the `k`-th smallest of these times (an order statistic). The expected value of the `k`-th order statistic increases with `k`.

### Improving the simple implementation
- **Durability**: add a WAL (append-only file) on leader before replying.
- **Reliability**: maintain replication log and retry failed followers (background catch-up).
- **Leader election**: integrate a consensus protocol (Raft) for leader failover.
- **Latency measurement**: gather p50/p95/p99, throughput, and CPU/memory metrics.
