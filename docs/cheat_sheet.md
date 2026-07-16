# WAL-G for PostgreSQL: Command & Configuration Cheat Sheet

This cheat sheet serves as a quick reference for database administrators and system engineers managing PostgreSQL backups with **WAL-G**.

---

## 1. Core CLI Commands

All commands below assume WAL-G is properly configured via environment variables or a configuration file.

### Backup Operations

*   **List Available Backups:**
    ```bash
    wal-g backup-list
    ```
    *Shows backup names, creation times, WAL segment boundaries, and sizes.*

*   **Push a Base Backup:**
    ```bash
    wal-g backup-push /var/lib/postgresql/data/
    ```
    *Initiates `pg_start_backup()`, streams and compresses files to cloud storage, calls `pg_stop_backup()`, and uploads the metadata.*

*   **Fetch a Base Backup (Restore):**
    ```bash
    wal-g backup-fetch /var/lib/postgresql/data/ LATEST
    ```
    *Downloads and extracts the latest base backup. You can replace `LATEST` with a specific backup name (e.g., `base_000000010000000000000003`).*

### WAL Archiving & Retrieval

PostgreSQL handles these automatically, but they can be run manually for troubleshooting:

*   **Push a WAL Segment:**
    ```bash
    wal-g wal-push pg_wal/000000010000000000000001
    ```
*   **Fetch a WAL Segment:**
    ```bash
    wal-g wal-fetch 000000010000000000000001 /var/lib/postgresql/data/pg_wal/000000010000000000000001
    ```
*   **Show WAL Archiving Status:**
    ```bash
    wal-g wal-show
    ```
    *Lists the WAL files that are in the archive storage and highlights gaps.*

### Cleanup & Retention

*   **List Backups and Retention Status:**
    ```bash
    wal-g delete garbage --confirm
    ```
    *Finds and lists backups/WALs that do not belong to any active backup chain or are corrupted.*

*   **Retain the Last N Backups (Delete Older):**
    ```bash
    wal-g delete retain FULL 5 --confirm
    ```
    *Keeps the 5 most recent base backups and deletes all older backups along with their associated WAL segments.*

*   **Delete Backups Older Than a Specific Date:**
    ```bash
    wal-g delete before base_000000010000000000000010 --confirm
    ```
    *Deletes all backups and WALs created before the specified backup name.*

---

## 2. Standard Configuration Settings

WAL-G is typically configured via environment variables.

### Storage Configuration (S3 Example)

| Environment Variable | Description | Example Value |
| :--- | :--- | :--- |
| `WALG_S3_PREFIX` | S3 path where backups/WALs are stored | `s3://prod-pg-backups/db-cluster-01` |
| `AWS_ACCESS_KEY_ID` | IAM User Access Key | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | IAM User Secret Key | `wJalrXUak7e5bVIWbRtmzCYYIPLKJHGFDS` |
| `AWS_ENDPOINT` | Custom endpoint for S3 compat (MinIO, Ceph) | `http://minio.internal:9000` |
| `AWS_S3_FORCE_PATH_STYLE`| Force path-style addressing (MinIO/local) | `true` |
| `AWS_REGION` | AWS Region | `us-east-1` |

### Database Connection Configuration

These are used by WAL-G during `backup-push` to run commands like `pg_start_backup()`:

| Environment Variable | Description | Default Value |
| :--- | :--- | :--- |
| `PGHOST` | PostgreSQL Hostname / Socket Dir | `/var/run/postgresql` |
| `PGPORT` | PostgreSQL Port | `5432` |
| `PGUSER` | PostgreSQL backup user | `postgres` |
| `PGDATABASE` | Database name to connect to | `postgres` |

---

## 3. Compression & Encryption Settings

### Compression Configuration

WAL-G supports several compression algorithms: `lz4` (default, fast), `zstd` (high ratio), `lzma`, `brotli`, and `gzip`.

*   **Set Compression Method:**
    ```bash
    export WALG_COMPRESSION_METHOD=zstd
    ```
*   **Set Compression Level (ZSTD ranges from 1 to 19):**
    ```bash
    export WALG_COMPRESSION_LEVEL=3
    ```

### Libsodium Symmetric Encryption

To secure backups before they leave the database server:

*   **Specify the Secret Key (Base64-encoded, 32 bytes):**
    ```bash
    export WALG_LIBSODIUM_KEY="yoursecretbase64keyhere..."
    export WALG_LIBSODIUM_KEY_TRANSFORM="base64"
    ```
*   **Alternative: Read Key from File:**
    ```bash
    export WALG_LIBSODIUM_KEY_PATH="/etc/wal-g/key.bin"
    ```

---

## 4. Performance & Concurrency Tuning

For large databases, tuning performance prevents system bottlenecking during backup cycles.

*   **Upload Concurrency (Parallel Workers):**
    ```bash
    export WALG_UPLOAD_CONCURRENCY=4
    ```
    *Determines how many files/parts WAL-G uploads in parallel during `backup-push`.*

*   **Download Concurrency (Parallel Workers):**
    ```bash
    export WALG_DOWNLOAD_CONCURRENCY=4
    ```
    *Determines how many files/parts WAL-G downloads in parallel during `backup-fetch`.*

*   **Disk Read Limit (Throttling):**
    ```bash
    export WALG_DISK_LIMIT_MBPS=100
    ```
    *Limits disk read speed (in MB/s) during backup to prevent starvation of the production disk I/O.*

*   **Network Bandwidth Limit (Throttling):**
    ```bash
    export WALG_NETWORK_LIMIT_MBPS=50
    ```
    *Limits upload speed (in MB/s) to prevent network saturation.*

---

## 5. Troubleshooting & Diagnostics

### Common Errors and Solutions

#### `invalid checkpoint record` / `could not locate required checkpoint record`
*   **Cause**: The PostgreSQL server was started in recovery mode but could not locate the start WAL segment (redo LSN) specified in the `backup_label`.
*   **Solution**:
    1. Ensure you have created the empty file `recovery.signal` (or `standby.signal` for replica) in the data directory.
    2. Confirm that `restore_command` is correctly set in `postgresql.auto.conf` or `postgresql.conf` and can execute `wal-g wal-fetch`.
    3. Verify that the WAL segments for the backup timeframe are present in the S3 bucket.

#### `Access Denied` / `S3 connection failed`
*   **Cause**: Incorrect IAM credentials, expired session, or incorrect S3 prefix permissions.
*   **Solution**:
    1. Test connectivity with `aws s3 ls <prefix>`.
    2. Ensure the IAM Policy grants both read and write rights (specifically `PutObject`, `GetObject`, `ListBucket`, and `DeleteObject` for cleanups).

#### `libsodium key not found` / `decryption error`
*   **Cause**: The recovery server does not have access to the matching symmetric key environment variable or file used to encrypt the backup.
*   **Solution**:
    1. Verify `WALG_LIBSODIUM_KEY` or `WALG_LIBSODIUM_KEY_PATH` is correctly exported before running `backup-fetch`.
    2. Ensure key permissions are locked down (`600`) so other processes cannot read it.
