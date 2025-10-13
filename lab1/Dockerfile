FROM python:3.11-slim

WORKDIR /app

# copy server and sample creator
COPY server.py client.py ./

EXPOSE 8000

# default args: serve /srv/site at port 8000
CMD ["python", "server.py", "/srv/site", "8000"]
