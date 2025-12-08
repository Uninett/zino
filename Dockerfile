# This Dockerfile is designed to run the Zino server backend
# Should be used in tandem with the provided docker compose file to ensure proper configuration

# Stage 1: Build stage
FROM python:3.12-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /zino
COPY . /zino

RUN python -m venv /venv
RUN /venv/bin/pip install --upgrade pip setuptools wheel
RUN /venv/bin/pip install .

# Stage 2: Runtime stage
FROM python:3.12-slim

WORKDIR /zino

COPY --from=build /venv /venv

ENV PATH="/venv/bin:$PATH"

ENTRYPOINT ["zino"]

# Run without arguments when none are provided
CMD []
