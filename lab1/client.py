import sys
import socket
import os

def recv_all(sock, nbytes):
    data = b""
    while len(data) < nbytes:
        chunk = sock.recv(min(4096, nbytes - len(data)))
        if not chunk:
            break
        data += chunk
    return data

def usage():
    print("Usage: python client.py server_host server_port filename [save_dir]")
    print("  filename: path on the server, e.g. index.html, /, books/crypto_lab2.pdf")
    print("  save_dir: optional directory to save binaries (default ./downloads)")
    sys.exit(1)

if len(sys.argv) < 4:
    usage()

host = sys.argv[1]
port = int(sys.argv[2])
filename = sys.argv[3]
save_dir = sys.argv[4] if len(sys.argv) > 4 else "./downloads"

# ensure filename begins with '/'
req_path = filename if filename.startswith("/") else "/" + filename

# create TCP connection
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((host, port))
    req = f"GET {req_path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    s.sendall(req.encode("utf-8"))

    # read headers
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
    if not buf:
        print("No response")
        sys.exit(1)

    headers_part, _, initial_body = buf.partition(b"\r\n\r\n")
    headers_text = headers_part.decode("iso-8859-1")
    header_lines = headers_text.split("\r\n")
    status_line = header_lines[0]
    parts = status_line.split(None, 2)
    status_code = int(parts[1]) if len(parts) > 1 else 0

    headers = {}
    for h in header_lines[1:]:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip().lower()] = v.strip()

    content_type = headers.get("content-type", "")
    content_length = int(headers["content-length"]) if "content-length" in headers else None

    if status_code != 200:
        print(f"Server returned {status_code}")
        # print any body as text
        if initial_body:
            try:
                print(initial_body.decode("utf-8", errors="replace"))
            except:
                print("<non-text body>")
        # read rest
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            try:
                print(chunk.decode("utf-8", errors="replace"))
            except:
                pass
        sys.exit(1)

    # if HTML -> print body as-is (text)
    if content_type.startswith("text/html"):
        body = initial_body
        if content_length is not None:
            needed = content_length - len(body)
            if needed > 0:
                body += recv_all(s, needed)
        else:
            # read until socket closes
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                body += chunk
        try:
            print(body.decode("utf-8", errors="replace"))
        except:
            print(body)
        sys.exit(0)

    # for PNG or PDF -> save file
    # decide filename to save: use last component of requested path
    save_name = os.path.basename(req_path.rstrip("/")) or "index"
    os.makedirs(save_dir, exist_ok=True)
    out_path = os.path.join(save_dir, save_name)
    body = initial_body
    if content_length is not None:
        needed = content_length - len(body)
        if needed > 0:
            body += recv_all(s, needed)
    else:
        # read until connection close
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            body += chunk

    with open(out_path, "wb") as f:
        f.write(body)
    print(f"Saved {out_path} (Content-Type: {content_type})")
