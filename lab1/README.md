
Source directory contents
```
lab1/
├─ site_content/
│  ├─ books/
│  │  └─ crypto_lab2.pdf
│  ├─ index.html
│  ├─ lab_caesar_crypto.pdf
│  ├─ should_look_like.png
├─ Dockerfile
├─ docker-compose.yml
├─ server.py
├─ README.md
```


docker-compose.yml
```
version: "3.8"
services:
  http-file-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PORT=8000
      - SERVE_DIR=/srv/site
    volumes:
      - ./site_content:/srv/site
    restart: unless-stopped
```


Dockerfile
```
FROM python:3.11-slim

WORKDIR /app

COPY server.py create_sample_content.py client.py ./

EXPOSE 8000

CMD ["python", "server.py", "/srv/site", "8000"]
```


How I start the container
```
docker compose up --build
```

Command that runs the server inside the container
```
python server.py /srv/site 8000
```


The contents of the served directory
```
├─ site_content/
│  ├─ books/
│  │  └─ crypto_lab2.pdf
│  ├─ index.html
│  ├─ lab_caesar_crypto.pdf
│  ├─ should_look_like.png
```


File not found:
![[Screenshot 2025-10-13 at 11.46.59.png]]


Request for the basic folder structure whcih defaults to the html page:
```
python3 client.py localhost 8000 /
```
Output:
```
<!doctype html><html><head><meta charset='utf-8'><title>Directory listing for /</title></head><body><h1>Directory listing for /</h1><hr>
<ul>
<li><a href="/books/">books/</a>
<ul>
<li><a href="/books/crypto_lab2.pdf">crypto_lab2.pdf</a></li>
</ul>
</li>
<li><a href="/lab_caesar_crypto.pdf">lab_caesar_crypto.pdf</a></li>
<li><a href="/page.html">page.html</a></li>
<li><a href="/should_look_like.png">should_look_like.png</a></li>
</ul>
<hr>
</body></html>
```

Request for a web page:
```
python3 client.py localhost 8000 /page.html
```
Output:
```
<!doctype html>
<html><head><meta charset="utf-8"><title>Test</title></head>
<body>
  <h3>Here is the html that should be returned from server</h3>
  <img src="should_look_like.png" alt="how it should look like">
  <p><a href="lab_caesar_crypto.pdf">Cifrul Cezar.pdf</a></p>
</body>
</html>
```

Request for a pdf:
```
python3 client.py localhost 8000 books/crypto_lab2.pdf
```
Output:
```
Saved ./downloads/crypto_lab2.pdf (Content-Type: application/pdf)
```




