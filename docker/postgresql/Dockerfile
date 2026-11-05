# syntax=docker/dockerfile:1.7
# =============================================================================
# Custom PostgreSQL Image
# Base: ghcr.io/cloudnative-pg/postgresql (Debian bookworm-slim)

# multi-stage build plan that pulls down a stable Debian Linux base, installs PostgreSQL 16, and manually compiles three critical security and utility extensions: pgaudit (for granular compliance logging), pg_cron (for running scheduled database tasks), and pgvector (for AI/embeddings support)

# compiles a pristine, hardened container image that runs under a secure, non-root user account (UID 26)
# =============================================================================

ARG PG_MAJOR=16
ARG PG_VERSION=16.4
ARG BASE_IMAGE=ghcr.io/cloudnative-pg/postgresql

# ── Stage 1: Build secure gosu from source with latest Go ────────────────────
FROM golang:1.26-bookworm AS gosu-builder
ENV CGO_ENABLED=0
RUN go install -ldflags "-w -s" github.com/tianon/gosu@latest

# ── Stage 2: Build custom extensions from source ─────────────────────────────
FROM ${BASE_IMAGE}:${PG_VERSION}-bookworm AS extensions-builder

ARG PG_MAJOR
USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    postgresql-server-dev-${PG_MAJOR} \
    libssl-dev \
    libkrb5-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Build pg_cron
RUN git clone --depth 1 --branch v1.6.4 https://github.com/citusdata/pg_cron.git /tmp/pg_cron \
    && cd /tmp/pg_cron && PG_CONFIG=/usr/lib/postgresql/${PG_MAJOR}/bin/pg_config make && PG_CONFIG=/usr/lib/postgresql/${PG_MAJOR}/bin/pg_config make install

# Build pgvector
RUN git clone --depth 1 --branch v0.7.4 https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector && PG_CONFIG=/usr/lib/postgresql/${PG_MAJOR}/bin/pg_config make && PG_CONFIG=/usr/lib/postgresql/${PG_MAJOR}/bin/pg_config make install

# ── Stage 2: Production image ─────────────────────────────────────────────────
FROM ${BASE_IMAGE}:${PG_VERSION}-bookworm AS production

ARG PG_MAJOR
ARG PG_VERSION

LABEL org.opencontainers.image.title="Custom PostgreSQL Platform"
LABEL org.opencontainers.image.description="Enterprise PostgreSQL with curated extensions"
LABEL org.opencontainers.image.version="${PG_VERSION}"
LABEL org.opencontainers.image.source="https://github.com/yourorg/postgres-platform"
LABEL org.opencontainers.image.vendor="Formsflow"
LABEL org.opencontainers.image.licenses="Apache-2.0"

USER root

# ── Patch all base image packages FIRST to clear any inherited CVEs ───────────
# This dedicated layer runs before any other installs so that packages like
# curl, libmariadb3, libgif7, and python3.11 from the base image are fully
# upgraded before extensions are layered on top.
RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

# Install production extensions and barman-cloud (required by CNPG for backup)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    lsb-release \
    curl \
    gnupg \
    && echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/apt.postgresql.org.gpg \
    && apt-get update && apt-get install -y --no-install-recommends \
    # Audit logging (SOC2 / PCI compliance)
    postgresql-${PG_MAJOR}-pgaudit \
    # OS-level execution statistics
    postgresql-${PG_MAJOR}-pg-stat-kcache \
    # Wait-event sampling
    postgresql-${PG_MAJOR}-pg-wait-sampling \
    # Geospatial
    postgresql-${PG_MAJOR}-postgis-3 \
    # TLS and CA certs
    ca-certificates \
    openssl \
    # barman-cloud: required by CNPG for WAL archive and basebackup
    barman-cli-cloud \
    python3-boto3 \
    python3-pip \
    && pip3 install --no-cache-dir --break-system-packages --upgrade \
       urllib3 cryptography pyjwt protobuf pyasn1 azure-core \
    && apt-get purge -y python3-pip \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy custom-built extensions
COPY --from=extensions-builder \
    /usr/lib/postgresql/${PG_MAJOR}/lib/pg_cron.so \
    /usr/lib/postgresql/${PG_MAJOR}/lib/vector.so \
    /usr/lib/postgresql/${PG_MAJOR}/lib/
COPY --from=extensions-builder \
    /usr/share/postgresql/${PG_MAJOR}/extension/pg_cron* \
    /usr/share/postgresql/${PG_MAJOR}/extension/vector* \
    /usr/share/postgresql/${PG_MAJOR}/extension/

# Overwrite vulnerable gosu in base image with secure version compiled with latest Go
COPY --from=gosu-builder /go/bin/gosu /usr/local/bin/gosu


# ── Optional: Corporate CA certificate ────────────────────────────────────────
# COPY ./certs/corporate-ca.crt /usr/local/share/ca-certificates/corporate-ca.crt
# RUN update-ca-certificates

# ── Security hardening ────────────────────────────────────────────────────────
# Grant the postgres user (26) ownership and ensure the directory is WRITABLE (700)
# Initdb needs to create files inside /var/lib/postgresql, so it MUST have write access
RUN chown -R 26:26 /var/lib/postgresql && \
    chown -R 26:26 /usr/lib/postgresql/${PG_MAJOR}/bin && \
    chmod 700 /var/lib/postgresql && \
    find /usr/lib/postgresql/${PG_MAJOR}/bin -type f -exec chmod 750 {} \;

# Verify binary integrity
RUN /usr/lib/postgresql/${PG_MAJOR}/bin/postgres --version && \
    /usr/lib/postgresql/${PG_MAJOR}/bin/pg_dump --version

# CNPG expects postgres user at UID 26
USER 26

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD pg_isready -U postgres || exit 1