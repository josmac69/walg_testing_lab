# WAL-G for PostgreSQL: Cloud-Native Backup & Recovery Documentation

This directory contains technical guides and references for **WAL-G**, the archival and recovery tool for PostgreSQL designed for cloud object storage.

## Contained Documents

*   **[Command & Configuration Cheat Sheet](file:///home/josef/github.com/josmac69/walg_testing_lab/docs/cheat_sheet.md)**: A quick-reference guide covering core CLI commands, configuration options, compression, client-side encryption settings, and common troubleshooting steps.
*   **[Production Runbooks](file:///home/josef/github.com/josmac69/walg_testing_lab/docs/production_runbooks.md)**: Step-by-step guides for installing and configuring WAL-G, scheduling daily base backups, monitoring archive status, performing full recoveries, executing Point-in-Time Recovery (PITR), setting up lifecycle retention pruning, and hardening backup security.
*   **[WAL-G Internals & Operations Report (PDF)](file:///home/josef/github.com/josmac69/walg_testing_lab/docs/WAL-G_Internals__A_Deep_Technical_Report_for_PostgreSQL_Specialists.pdf)**: A deep-dive technical analysis of WAL-G's architecture, covering parallel block-level compression, background uploading daemons, delta-backup mechanisms, and cloud storage providers.
