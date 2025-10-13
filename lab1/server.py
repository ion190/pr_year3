import os
import sys
import socket
import urllib.parse
from datetime import datetime
from html import escape

ALLOWED_EXT = {
    ".html": "text/html",
    ".htm":  "text/html",
    ".png":  "image/png",
    ".pdf":  "application/pdf",
}

def send_response(conn, status_code, reason, headers=None, body=b""):
    if headers is None:
        headers = {}
    status_line = f"HTTP/1.1 {status_code} {reason}\r\n"
    header_lines = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
    resp = (status_line + header_lines + "\r\n").encode("utf-8") + body
    conn.sendall(resp)

def make_dir_listing_html(base_url_path, abs_dir, rel_path, recurse_root=False, max_depth=10):
    def make_header(title):
        return (
            "<!doctype html>"
            "<html><head><meta charset='utf-8'><title>%s</title></head><body>"
            "<h1>%s</h1><hr>" % (escape(title), escape(title))
        )
    def make_footer():
        return "</body></html>"
    def rel_to_url(rel):
        url = "/" + rel.replace(os.path.sep, "/")
        return urllib.parse.quote(url)

    def build_non_recursive(abs_dir, rel_path):
        entries = sorted(os.listdir(abs_dir))
        lines = ["<ul>"]
        if rel_path:
            parent = os.path.dirname(rel_path.rstrip("/"))
            parent_url = "/" + parent + "/" if parent else "/"
            lines.append(f'<li><a href="{escape(parent_url)}">.. (parent)</a></li>')
        for name in entries:
            full = os.path.join(abs_dir, name)
            display = escape(name + ("/" if os.path.isdir(full) else ""))
            url = rel_to_url(os.path.join(rel_path, name)) if rel_path else rel_to_url(name)
            if os.path.isdir(full):
                url = url.rstrip("/") + "/"
            lines.append(f'<li><a href="{url}">{display}</a></li>')
        lines.append("</ul>")
        return "\n".join(lines)

    def build_recursive(abs_dir, rel_prefix, depth):
        if depth > max_depth:
            return "<ul><li><em>Max recursion depth reached</em></li></ul>"
        try:
            entries = sorted(os.listdir(abs_dir))
        except PermissionError:
            return "<ul><li><em>Permission denied</em></li></ul>"

        html_parts = ["<ul>"]
        for name in entries:
            full = os.path.join(abs_dir, name)
            rel = os.path.join(rel_prefix, name) if rel_prefix else name
            display = escape(name + ("/" if os.path.isdir(full) else ""))
            url = "/" + rel.replace(os.path.sep, "/")
            url = urllib.parse.quote(url)
            if os.path.isdir(full):
                dir_url = url.rstrip("/") + "/"
                html_parts.append(f'<li><a href="{dir_url}">{display}</a>')
                html_parts.append(build_recursive(full, rel, depth + 1))
                html_parts.append("</li>")
            else:
                html_parts.append(f'<li><a href="{url}">{display}</a></li>')
        html_parts.append("</ul>")
        return "\n".join(html_parts)

    title = f"Directory listing for /{rel_path}" if rel_path else "Directory listing for /"
    html = [make_header(title)]
    if recurse_root and (rel_path == "" or rel_path is None):
        # recursive listing for root only
        html.append(build_recursive(abs_dir, "", depth=0))
    else:
        html.append(build_non_recursive(abs_dir, rel_path))
    html.append("<hr>")
    html.append(make_footer())
    return "\n".join(html).encode("utf-8")


def handle_client(conn, serve_dir):
    try:
        # read request until header end
        request = b""
        while b"\r\n\r\n" not in request:
            chunk = conn.recv(1024)
            if not chunk:
                break
            request += chunk
        if not request:
            return

        try:
            first_line = request.splitlines()[0].decode("utf-8")
        except Exception:
            send_response(conn, "400", "Bad Request", {"Content-Type": "text/plain"}, b"Bad Request")
            return

        parts = first_line.split()
        if len(parts) < 2:
            send_response(conn, "400", "Bad Request", {"Content-Type": "text/plain"}, b"Bad Request")
            return

        method, raw_path = parts[0], parts[1]
        if method.upper() != "GET":
            body = b"<html><body><h1>405 Method Not Allowed</h1></body></html>"
            send_response(conn, "405", "Method Not Allowed", {
                "Content-Type": "text/html",
                "Content-Length": str(len(body)),
                "Connection": "close"
            }, body)
            return

        path = urllib.parse.unquote(raw_path)
        # normalize path: strip leading '/', keep trailing slash if present
        if path.startswith("/"):
            path = path[1:]
        rel_path = path  # path relative to serve_dir (may be "")

        # >>> NEW: treat explicit requests for index.html/index.htm as root directory
        if rel_path.lower() in ("index.html", "index.htm"):
            rel_path = ""

        if rel_path == "":
            target_abs = os.path.abspath(serve_dir)
        else:
            target_abs = os.path.abspath(os.path.join(serve_dir, rel_path))

        serve_dir_abs = os.path.abspath(serve_dir)
        # prevent directory traversal
        if not target_abs.startswith(serve_dir_abs):
            body = b"<html><body><h1>404 Not Found</h1></body></html>"
            send_response(conn, "404", "Not Found", {
                "Content-Type": "text/html",
                "Content-Length": str(len(body)),
                "Connection": "close"
            }, body)
            return

        # If target is directory or requested with trailing slash -> directory listing
        if os.path.isdir(target_abs):
            # For root (rel_path == ""), produce a recursive listing
            recurse_root = (rel_path == "" or rel_path is None)
            listing = make_dir_listing_html("/", target_abs, rel_path if rel_path else "", recurse_root=recurse_root)
            headers = {
                "Content-Type": "text/html; charset=utf-8",
                "Content-Length": str(len(listing)),
                "Connection": "close",
                "Date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
            }
            send_response(conn, "200", "OK", headers, listing)
            return

        # Otherwise target must be a file
        if not os.path.isfile(target_abs):
            body = b"<html><body><h1>404 Not Found</h1></body></html>"
            send_response(conn, "404", "Not Found", {
                "Content-Type": "text/html",
                "Content-Length": str(len(body)),
                "Connection": "close"
            }, body)
            return

        ext = os.path.splitext(target_abs)[1].lower()
        if ext not in ALLOWED_EXT:
            body = b"<html><body><h1>404 Not Found (unsupported type)</h1></body></html>"
            send_response(conn, "404", "Not Found", {
                "Content-Type": "text/html",
                "Content-Length": str(len(body)),
                "Connection": "close"
            }, body)
            return

        # read file and respond
        with open(target_abs, "rb") as f:
            body = f.read()
        headers = {
            "Content-Type": ALLOWED_EXT[ext],
            "Content-Length": str(len(body)),
            "Connection": "close",
            "Date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        }
        send_response(conn, "200", "OK", headers, body)
    except Exception as e:
        try:
            body = f"<html><body><h1>500 Internal Server Error</h1><pre>{e}</pre></body></html>".encode("utf-8")
            send_response(conn, "500", "Internal Server Error", {
                "Content-Type": "text/html",
                "Content-Length": str(len(body)),
                "Connection": "close"
            }, body)
        except Exception:
            pass


def main():
    serve_dir = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SERVE_DIR", "./site_content")
    port = int(sys.argv[2]) if len(sys.argv) > 2 else int(os.environ.get("PORT", "8000"))

    serve_dir = os.path.abspath(serve_dir)
    if not os.path.isdir(serve_dir):
        print("Empty directory")
    else:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", port))
            s.listen(1)  # single-connection backlog
            print(f"Serving {serve_dir} on 0.0.0.0:{port} (single-threaded)")

            while True:
                conn, addr = s.accept()
                print("Connection from", addr)
                with conn:
                    handle_client(conn, serve_dir)
                print("Connection closed")

if __name__ == "__main__":
    main()
