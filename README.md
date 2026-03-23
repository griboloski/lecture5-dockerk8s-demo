# Lecture 5: Docker & Kubernetes for Scalable Deployment

**DevOps for Cyber-Physical Systems (HS 2026)**

**Forked Repository:** https://github.com/griboloski/lecture5-dockerk8s-demo

**Docker Hub Username:** `griboloski`

---

## Table of Contents
- [Setup](#setup)
- [Task 1a: Add Adminer Service](#task-1a-add-adminer-service)
- [Task 1b: Change Base Image to Alpine](#task-1b-change-base-image-to-alpine)
- [Task 2a: Image Tagging and Registry](#task-2a-image-tagging-and-registry)
- [Task 2b: Container Inspection](#task-2b-container-inspection)
- [Task 3a: Deploy to Kubernetes](#task-3a-deploy-to-kubernetes)
- [Task 3b: Scale and Test Load Balancing](#task-3b-scale-and-test-load-balancing)
- [Task 3c: Self-Healing](#task-3c-self-healing)

---

## Setup

Prerequisites installed:
- Docker Desktop 28.5.1 (Kubernetes enabled via Docker Desktop settings)
- kubectl v1.34.1
- Python 3.12

Clone and run:
```bash
git clone https://github.com/griboloski/lecture5-dockerk8s-demo .
docker compose up -d
# App available at http://localhost:5000
```

---

## Task 1a: Add Adminer Service

### What was changed

Added an `adminer` service to `docker-compose.yml` following the same pattern as the existing services:

```yaml
adminer:
  image: adminer:latest
  container_name: lecture5-adminer
  ports:
    - "8080:8080"
  environment:
    - ADMINER_DEFAULT_SERVER=db
  depends_on:
    - db
  networks:
    - app-network
  restart: unless-stopped
```

### Testing

```bash
docker compose up -d
# Open http://localhost:8080
# Login: System=PostgreSQL, Server=db, Username=taskuser, Password=taskpass, Database=taskdb
```

Adminer at http://localhost:8080 — tasks table structure in taskdb:

![Adminer tasks table](Screenshots/adminer-tasks.png)

---

## Task 1b: Change Base Image to Alpine

### What was changed

Modified `Dockerfile` to use `python:3.11-alpine` instead of `python:3.11-slim`.

**Key difference:** Alpine uses `apk` instead of `apt-get` and uses musl libc instead of glibc. Since `psycopg2-binary` ships a musllinux pre-built wheel, only the `libpq` runtime library is needed.

```dockerfile
FROM python:3.11-alpine

WORKDIR /app

# Only libpq runtime needed -- psycopg2-binary uses pre-built musllinux wheel
RUN apk add --no-cache libpq

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ templates/
COPY assets/ assets/

EXPOSE 5000
CMD ["python", "app.py"]
```

### Size Comparison

```
REPOSITORY   TAG       SIZE
task-app     alpine    128MB
task-app     slim      232MB
```

**Alpine is 45% smaller** (128MB vs 232MB).

### Build Issues Encountered

**First attempt:** Added `gcc musl-dev postgresql-dev` for psycopg2 compilation. This pulled in 45 packages including LLVM/Clang, resulting in a **1.04GB** image — larger than slim!

**Fix:** Realized `psycopg2-binary` ships a pre-built `musllinux_1_1_x86_64` wheel for Alpine. Only `libpq` (runtime shared library) is needed. Removing the build toolchain reduced the image to **128MB**.

---

## Task 2a: Image Tagging and Registry

### Commands Used

```bash
docker build -t task-app:v1.0 .
docker tag task-app:v1.0 griboloski/lecture5-webapp:v1.0
docker push griboloski/lecture5-webapp:v1.0
```

**Docker Hub image:** https://hub.docker.com/r/griboloski/lecture5-webapp

![Docker Hub](Screenshots/dockerhub.png)

---

## Task 2b: Container Inspection

### `docker compose logs web`

**What it shows:** Streams the stdout/stderr output from the `web` container — Flask startup messages, incoming HTTP request logs, errors, and debug output. Useful for diagnosing application issues without exec-ing into the container.

### `docker inspect lecture5-web`

**What it shows:** Returns a detailed JSON object with the container's full configuration and runtime state, including:
- Container ID, image SHA, creation time
- Running state (PID, start time, exit code)
- Network settings (IP address, MAC address, connected networks)
- Volume mounts (e.g., `app.py` and `templates/` mounted read-only)
- Environment variables (DB_HOST, DB_USER, REDIS_HOST, etc.)
- Restart policy (`unless-stopped`)
- Port bindings (`5000/tcp -> 0.0.0.0:5000`)

Useful for debugging networking issues or verifying configuration is applied correctly.

### `docker stats`

**What it shows:** A live, updating table of real-time resource usage for all running containers: CPU%, memory usage vs limit, network I/O (bytes sent/received), and block I/O (disk reads/writes). Useful for identifying resource-hungry containers or memory leaks.

---

## Task 3a: Deploy to Kubernetes

### Steps

```bash
# Kubernetes enabled via Docker Desktop Settings -> Kubernetes -> Enable Kubernetes
kubectl apply -f k8s-backend.yaml
kubectl apply -f k8s-web.yaml
```

`k8s-web.yaml` was updated to use `griboloski/lecture5-webapp:v1.0` (our Docker Hub image).

App accessible at `http://localhost` (port 80 via LoadBalancer, Docker Desktop assigns `localhost` as external IP).

![kubectl get pods](Screenshots/kuberctl-pods.png)

![App in browser](Screenshots/app-browser.png)

---

## Task 3b: Scale and Test Load Balancing

### Commands

```bash
kubectl scale deployment lecture5-web --replicas=5
PYTHONIOENCODING=utf-8 python test_load_balancing.py
```

### Load Balancing Test Output

![Load balancing test](Screenshots/load-balancing.png)

### How Kubernetes Distributes Traffic

Kubernetes distributes traffic using a **Service** object (`lecture5-web-service` of type LoadBalancer). The Service maintains a list of healthy pod endpoints and uses **kube-proxy** to implement load balancing via iptables/IPVS rules on each node. When a request arrives at the Service's virtual IP, kube-proxy randomly selects one of the backing pod endpoints to forward it to. The endpoint list is automatically updated by the Endpoints controller as pods start, stop, or fail readiness probes, ensuring traffic only reaches ready pods even during rolling updates.

---

## Task 3c: Self-Healing

**Before deletion** (5 pods running):

![Before deletion](Screenshots/self-healing-before.png)

**Delete a pod:**
```bash
kubectl delete pod lecture5-web-7f867c76d-7tcr9
```

**During healing** — replacement pod `qlvp5` already Running at 17s:

![During healing](Screenshots/self-healing-during.png)

**Fully recovered:**

![After healing](Screenshots/self-healing-after.png)

Pod `7tcr9` was replaced by `qlvp5` within seconds. The deployment stayed at 5 replicas throughout with zero manual intervention.

### Why Self-Healing is Important

Self-healing is critical because pods can fail unexpectedly due to OOM kills, application crashes, node hardware failures, or OS-level issues. Kubernetes' **ReplicaSet controller** continuously reconciles the actual running pod count against the desired replica count and automatically creates replacement pods when a deficit is detected. This guarantees service availability without any manual operator intervention, meaning a 5-replica deployment automatically stays at 5 replicas even under failure conditions — a crucial property for production deployments of cyber-physical systems where downtime can have real-world consequences.

---

## Issues Encountered and Solutions

| Issue | Solution |
|-------|----------|
| Alpine image was 1.04GB (larger than slim) | Removed unnecessary build tools; only `libpq` runtime needed since psycopg2-binary uses a pre-built musllinux wheel |
| `docker login` non-interactive in bash | Logged in via Docker Desktop GUI instead |
| Kubernetes not configured after enabling | Had to click "Apply & Restart" in Docker Desktop settings and wait ~2 min |
| `test_load_balancing.py` pointed to minikube URL (port 63501) | Updated `SERVICE_URL` to `http://localhost/info` for Docker Desktop LoadBalancer |
| UnicodeEncodeError with emoji in Python on Windows | Set `PYTHONIOENCODING=utf-8` environment variable |
