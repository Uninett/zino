# This Dockerfile is designed to run the Zino server backend
# Should be used in tandem with the provided docker compose file to ensure proper configuration

# Stage 1: Build stage
FROM python:3.12-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /zino

COPY src /zino/src
COPY pyproject.toml /zino/pyproject.toml

# Copied to allow for version inference
COPY .git/HEAD /zino/.git/HEAD
COPY .git/refs /zino/.git/refs
COPY .git/objects /zino/.git/objects

RUN python -m venv /venv
RUN /venv/bin/pip install --upgrade pip setuptools wheel
RUN /venv/bin/pip install .

# Stage 2: Runtime stage
FROM python:3.12-slim

WORKDIR /zino

COPY --from=build /venv /venv
COPY --from=build /zino /zino

ENV PATH="/venv/bin:$PATH"

ENTRYPOINT ["zino"]

# Run without arguments when none are provided
CMD []
