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

All 4 services running after `docker compose up -d`:

```
NAME               IMAGE                STATUS
lecture5-adminer   adminer:latest       Up  0.0.0.0:8080->8080/tcp
lecture5-db        postgres:15-alpine   Up (healthy)   0.0.0.0:5432->5432/tcp
lecture5-redis     redis:7-alpine       Up (healthy)   0.0.0.0:6379->6379/tcp
lecture5-web       exercise5-web        Up  0.0.0.0:5000->5000/tcp
```

**Screenshot placeholder:** Adminer accessible at http://localhost:8080, tasks table visible after login with taskuser/taskpass/taskdb.

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

**Lesson:** Always check if a package provides a binary wheel before adding build dependencies to Alpine images.

---

## Task 2a: Image Tagging and Registry

### Commands Used

```bash
# Build the image with version tag
docker build -t task-app:v1.0 .

# Tag for Docker Hub
docker tag task-app:v1.0 griboloski/lecture5-webapp:v1.0

# Push to Docker Hub
docker push griboloski/lecture5-webapp:v1.0
```

**Docker Hub image:** https://hub.docker.com/r/griboloski/lecture5-webapp

The image is published at `griboloski/lecture5-webapp:v1.0` (Alpine-based, 128MB).

**Screenshot placeholder:** Docker Hub page showing `griboloski/lecture5-webapp` with tag `v1.0`.

---

## Task 2b: Container Inspection

### `docker compose logs web`

```
lecture5-web  | Database initialized successfully!
lecture5-web  |  * Serving Flask app 'app'
lecture5-web  |  * Debug mode: on
lecture5-web  |  * Running on all addresses (0.0.0.0)
lecture5-web  |  * Running on http://127.0.0.1:5000
lecture5-web  |  * Running on http://172.18.0.5:5000
```

**What it shows:** Streams the stdout/stderr output from the `web` container — Flask startup messages, incoming HTTP request logs, errors, and debug output. Useful for diagnosing application issues without exec-ing into the container.

### `docker inspect lecture5-web`

**What it shows:** Returns a detailed JSON object with the container's full configuration and runtime state, including:
- Container ID, image SHA, creation time
- Running state (PID, start time, exit code)
- Network settings (IP address: `172.18.0.5`, MAC address, connected networks)
- Volume mounts (e.g., `app.py` and `templates/` mounted read-only)
- Environment variables (DB_HOST, DB_USER, REDIS_HOST, etc.)
- Restart policy (`unless-stopped`)
- Port bindings (`5000/tcp -> 0.0.0.0:5000`)

Useful for debugging networking issues or verifying configuration is applied correctly.

### `docker stats`

```
NAME               CPU %    MEM USAGE / LIMIT     NET I/O           BLOCK I/O
lecture5-adminer   0.01%    8.457MiB / 7.674GiB   1.9kB / 126B      0B / 0B
lecture5-web       0.20%    56.97MiB / 7.674GiB   3.7kB / 3.38kB    0B / 311kB
lecture5-db        0.03%    30.91MiB / 7.674GiB   5.33kB / 2.91kB   0B / 52.4MB
lecture5-redis     0.72%    3.266MiB / 7.674GiB   2.12kB / 126B     0B / 0B
```

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

### Result

```
NAME                           READY   STATUS    RESTARTS   AGE
lecture5-web-7f867c76d-5rlqn   1/1     Running   0          29s
lecture5-web-7f867c76d-7tcr9   1/1     Running   0          29s
lecture5-web-7f867c76d-wtstl   1/1     Running   0          29s
postgres-5695fbfd64-lcrxk      1/1     Running   0          30s
redis-57566c54f6-lr6rz         1/1     Running   0          30s

NAME                   TYPE           CLUSTER-IP       EXTERNAL-IP   PORT(S)
db                     ClusterIP      10.109.190.243   <none>        5432/TCP
lecture5-web-service   LoadBalancer   10.101.208.84    localhost     80:32057/TCP
redis                  ClusterIP      10.100.229.134   <none>        6379/TCP
```

App accessible at `http://localhost` (port 80 via LoadBalancer, Docker Desktop assigns `localhost` as external IP).

**Screenshot placeholder:** Browser showing app at http://localhost + `kubectl get pods` output.

---

## Task 3b: Scale and Test Load Balancing

### Commands

```bash
kubectl scale deployment lecture5-web --replicas=5
PYTHONIOENCODING=utf-8 python test_load_balancing.py
```

### Load Balancing Test Output

```
Testing load balancing across pods...
Service URL: http://localhost/info
Making 20 requests...

Request  1: Served by lecture5-web-7f867c76d-ss8pw
Request  2: Served by lecture5-web-7f867c76d-ss8pw
Request  3: Served by lecture5-web-7f867c76d-wtstl
Request  4: Served by lecture5-web-7f867c76d-wtstl
Request  5: Served by lecture5-web-7f867c76d-wtstl
Request  6: Served by lecture5-web-7f867c76d-5rlqn
Request  7: Served by lecture5-web-7f867c76d-7tcr9
Request  8: Served by lecture5-web-7f867c76d-7tcr9
Request  9: Served by lecture5-web-7f867c76d-5rlqn
Request 10: Served by lecture5-web-7f867c76d-tpsh2
Request 11: Served by lecture5-web-7f867c76d-ss8pw
Request 12: Served by lecture5-web-7f867c76d-5rlqn
Request 13: Served by lecture5-web-7f867c76d-wtstl
Request 14: Served by lecture5-web-7f867c76d-ss8pw
Request 15: Served by lecture5-web-7f867c76d-ss8pw
Request 16: Served by lecture5-web-7f867c76d-5rlqn
Request 17: Served by lecture5-web-7f867c76d-wtstl
Request 18: Served by lecture5-web-7f867c76d-tpsh2
Request 19: Served by lecture5-web-7f867c76d-5rlqn
Request 20: Served by lecture5-web-7f867c76d-5rlqn

============================================================
LOAD BALANCING RESULTS
============================================================

Total successful requests: 20
Number of unique pods serving requests: 5

lecture5-web-7f867c76d-5rlqn:  6 requests ( 30.0%) ||||||
lecture5-web-7f867c76d-ss8pw:  5 requests ( 25.0%) |||||
lecture5-web-7f867c76d-wtstl:  5 requests ( 25.0%) |||||
lecture5-web-7f867c76d-7tcr9:  2 requests ( 10.0%) ||
lecture5-web-7f867c76d-tpsh2:  2 requests ( 10.0%) ||

============================================================
SUCCESS: Load balancing is working!
   Traffic distributed across 5 pods
============================================================
```

### How Kubernetes Distributes Traffic

Kubernetes distributes traffic using a **Service** object (`lecture5-web-service` of type LoadBalancer). The Service maintains a list of healthy pod endpoints and uses **kube-proxy** to implement load balancing via iptables/IPVS rules on each node. When a request arrives at the Service's virtual IP, kube-proxy randomly selects one of the backing pod endpoints to forward it to. The endpoint list is automatically updated by the Endpoints controller as pods start, stop, or fail readiness probes, ensuring traffic only reaches ready pods even during rolling updates.

---

## Task 3c: Self-Healing

### Commands and Output

**Before deletion (5 pods running):**
```
NAME                           READY   STATUS    RESTARTS   AGE
lecture5-web-7f867c76d-5rlqn   1/1     Running   0          98s
lecture5-web-7f867c76d-7tcr9   1/1     Running   0          98s
lecture5-web-7f867c76d-ss8pw   1/1     Running   0          59s
lecture5-web-7f867c76d-tpsh2   1/1     Running   0          59s
lecture5-web-7f867c76d-wtstl   1/1     Running   0          98s
```

**Delete a pod:**
```bash
kubectl delete pod lecture5-web-7f867c76d-5rlqn
```

**During healing (~2 seconds after deletion):**
```
NAME                           READY   STATUS    RESTARTS   AGE
lecture5-web-7f867c76d-7tcr9   1/1     Running   0          104s
lecture5-web-7f867c76d-mzw5z   1/1     Running   0          4s    <- NEW replacement pod
lecture5-web-7f867c76d-ss8pw   1/1     Running   0          65s
lecture5-web-7f867c76d-tpsh2   1/1     Running   0          65s
lecture5-web-7f867c76d-wtstl   1/1     Running   0          104s
```

**After healing (fully recovered):**
```
NAME                           READY   STATUS    RESTARTS   AGE
lecture5-web-7f867c76d-7tcr9   1/1     Running   0          113s
lecture5-web-7f867c76d-mzw5z   1/1     Running   0          13s
lecture5-web-7f867c76d-ss8pw   1/1     Running   0          74s
lecture5-web-7f867c76d-tpsh2   1/1     Running   0          74s
lecture5-web-7f867c76d-wtstl   1/1     Running   0          113s
```

Pod `5rlqn` was replaced by `mzw5z` within **4 seconds**. The deployment stayed at 5 replicas throughout with zero manual intervention.

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
