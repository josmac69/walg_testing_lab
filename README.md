# PostgreSQL WAL-G Testing Lab

Welcome to the **PostgreSQL WAL-G Testing Lab**. This repository contains hands-on, containerized examples designed to demonstrate how to use **WAL-G** for backing up, archiving, securing, and restoring PostgreSQL databases.

WAL-G is an archival and restoration tool for databases (PostgreSQL, MySQL, MongoDB, Redis) and is the successor to the widely-used WAL-E tool. It is written in Go and optimized for high-throughput, low-overhead database backups.

---

## Lab Directory Structure

This lab is split into two independent examples located in their respective subdirectories:

1. **[01_basic_pitr](./01_basic_pitr)**
   - **Goal:** Demonstrates basic basebackups, continuous WAL archiving, and **Point-in-Time Recovery (PITR)**.
   - **Storage:** Emulated S3 storage bucket using MinIO.
   - **Scenario:** Backs up initial data, adds new data, simulates an accidental table drop, and restores the database to the exact millisecond before the table was dropped.

2. **[02_encryption_compression](./02_encryption_compression)**
   - **Goal:** Focuses on backup security and storage optimization using client-side encryption and high-efficiency compression.
   - **Security:** Client-side symmetric encryption using **Libsodium** (a 32-byte key generated dynamically).
   - **Compression:** High-performance **Zstandard (zstd)** compression.
   - **Scenario:** Backs up sensitive credentials using encryption and compression, drops the credentials, and restores them securely.

---

## Prerequisites

Before running these labs, ensure your local machine has the following tools installed:

- **Docker** (v20.10+)
- **Docker Compose** (v2.0+)
- **GNU Make** (installed by default on most Linux and macOS systems)
- **OpenSSL** (used in Lab 02 to generate cryptographic keys)

---

## Quick Start (Example 1: PITR)

To get started quickly with the basic PITR flow:

```bash
# Navigate to the first lab
cd 01_basic_pitr

# Start services (PostgreSQL + MinIO)
make up

# Seed initial test data
make init-db

# Trigger a WAL-G base backup
make backup

# Insert more data (which gets archived via WAL logs)
make add-data

# Simulate an accidental table drop (disaster)
make disaster

# Run Point-in-Time Recovery to restore the table
make restore

# Verify data was restored successfully
make verify

# Tear down the lab environment and volumes
make down
```

For more details about each step and how WAL-G handles file transfers under the hood, check the respective lab subdirectories!

---

## Documentation & Runbooks

Comprehensive guides and operational references are available in the **[docs](./docs)** directory:

- **[Command & Configuration Cheat Sheet](./docs/cheat_sheet.md)**: A quick-reference guide covering core CLI commands, configuration options, compression, client-side encryption settings, and common troubleshooting steps.
- **[Production Runbooks](./docs/production_runbooks.md)**: Step-by-step guides for installing and configuring WAL-G, scheduling daily base backups, monitoring archive status, performing full recoveries, executing Point-in-Time Recovery (PITR), setting up lifecycle retention pruning, and hardening backup security.
- **[WAL-G Internals & Operations Report (PDF)](./docs/WAL-G_Internals__A_Deep_Technical_Report_for_PostgreSQL_Specialists.pdf)**: A deep-dive technical analysis of WAL-G's architecture, covering parallel block-level compression, background uploading daemons, delta-backup mechanisms, and cloud storage providers.