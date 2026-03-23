# ============================================================
# Lecture 5: Docker Demo - Dockerfile
# DevOps for Cyber-Physical Systems | University of Bern
# ============================================================
# This Dockerfile demonstrates the basics of containerizing
# a Python web application.
# ============================================================

# STEP 1: Start with official Python image
# ----------------------------------------------------------
# We use Alpine for minimal image size (~50MB vs ~150MB for slim)
FROM python:3.11-alpine

# STEP 2: Set the working directory
# ----------------------------------------------------------
# All subsequent commands run from /app
WORKDIR /app

# STEP 3: Install system dependencies required for psycopg2-binary
# ----------------------------------------------------------
# psycopg2-binary bundles its own libpq on Alpine (musllinux wheel).
# We only need the libpq runtime library; no compiler required
# since we use the pre-built binary wheel.
RUN apk add --no-cache libpq

# STEP 4: Copy and install dependencies FIRST
# ----------------------------------------------------------
# Why separate? Docker layer caching!
# If requirements.txt hasn't changed, this layer is cached
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# STEP 4: Copy application code
# ----------------------------------------------------------
# This layer rebuilds when code changes, but dependencies stay cached
COPY app.py .
COPY templates/ templates/
COPY assets/ assets/

# STEP 5: Expose the port
# ----------------------------------------------------------
# Documents which port the app uses (doesn't publish it)
EXPOSE 5000

# STEP 6: Run the application
# ----------------------------------------------------------
# CMD defines what runs when the container starts
CMD ["python", "app.py"]

# ============================================================
# BUILD:  docker build -t lecture5-webapp .
# RUN:    docker run -p 5000:5000 lecture5-webapp
# ============================================================