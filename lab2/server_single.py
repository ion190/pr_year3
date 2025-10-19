import os, time, html
from http.server import SimpleHTTPRequestHandler, HTTPServer

HITS = {}

class Handler(SimpleHTTPRequestHandler):
    SIM_DELAY_S = float(os.getenv("SIM_DELAY_S", "1.0"))

    def do_GET(self):
        path = self.path.split('?',1)[0]
        HITS[path] = HITS.get(path, 0) + 1
        time.sleep(self.SIM_DELAY_S)
        return super().do_GET()

    def list_directory(self, path):
        try:
            listing = os.listdir(path)
        except OSError:
            self.send_error(404)
            return None
        listing.sort(key=str.lower)
        enc = "utf-8"
        self.send_response(200)
        self.send_header("Content-type", f"text/html; charset={enc}")
        self.end_headers()

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
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
