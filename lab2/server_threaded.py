import os, time, html, threading, collections
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timedelta

SIM_DELAY_S = float(os.getenv("SIM_DELAY_S", "1.0"))
DEMO_RACE = os.getenv("DEMO_RACE", "false").lower() == "true"
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "5"))
WINDOW = timedelta(seconds=1)

# shared state
HITS = collections.defaultdict(int)
HITS_LOCK = threading.Lock()

REQUEST_TIMES = collections.defaultdict(collections.deque)
RL_LOCK = threading.Lock()

class Handler(SimpleHTTPRequestHandler):
    def _rate_limited(self) -> bool:
        ip = self.client_address[0]
        now = datetime.now()
        with RL_LOCK:
            q = REQUEST_TIMES[ip]
            while q and now - q[0] > WINDOW:
                q.popleft()
            if len(q) >= RATE_LIMIT:
                return True
            q.append(now)
            return False

    def _inc_hit_naive(self, key: str):
        v = HITS.get(key, 0)
        time.sleep(0.002)        # force interleaving to expose race
        HITS[key] = v + 1        # lost-update risk

    def _inc_hit_locked(self, key: str):
        with HITS_LOCK:
            HITS[key] += 1

    def do_GET(self):
        if self._rate_limited():
            self.send_response(429, "Too Many Requests")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Too Many Requests\n")
            return

        path = self.path.split('?',1)[0]
        if DEMO_RACE:
            self._inc_hit_naive(path)
        else:
            self._inc_hit_locked(path)

        time.sleep(SIM_DELAY_S)
        return super().do_GET()

    def list_directory(self, path):
        try:
            listing = os.listdir(path)
        except OSError:
            self.send_error(404); return None
        listing.sort(key=str.lower)
        enc = "utf-8"
        self.send_response(200)
        self.send_header("Content-type", f"text/html; charset={enc}")
        self.end_headers()

        with HITS_LOCK:
            def hit_for(name):
                base = self.path.rstrip('/')
                key = (base + '/' + name) if base else '/' + name
                return HITS.get(key, 0)
            rows = "\n".join(
                f"<tr><td><a href='{html.escape(name)}'>{html.escape(name)}</a></td>"
                f"<td style='text-align:right'>{hit_for(name)}</td></tr>"
                for name in listing
            )
        body = f"""<!doctype html>
<html><head><title>Directory listing for {html.escape(self.path)}</title></head>
<body><h1>Directory listing for {html.escape(self.path)}</h1>
<table border=1 cellpadding=4 cellspacing=0>
<tr><th>File / Directory</th><th>Hits</th></tr>
{rows}
</table></body></html>"""
        self.wfile.write(body.encode(enc))
        return None

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
