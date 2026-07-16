# WAL-G for PostgreSQL: Production Runbooks

This document provides step-by-step operational runbooks for managing WAL-G in a production PostgreSQL environment.

---

## Runbook 1: Initial Setup and Configuration

Use this runbook to enable WAL-G backups on a new PostgreSQL instance.

### Prerequisites
* PostgreSQL 12+ installed.
* WAL-G binary installed in `/usr/local/bin/wal-g` with execution permissions (`chmod +x`).
* Cloud storage bucket (e.g., S3) created and IAM permissions configured.

### Step 1: Configure Environment Variables
Create a configuration file to store the credentials. Do not write credentials directly in PostgreSQL config files.
Create `/etc/wal-g.d/env`:
```ini
WALG_S3_PREFIX=s3://my-prod-bucket/pg-backups
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUak7e5bVIWbRtmzCYYIPLKJHGFDS
AWS_REGION=us-east-1
WALG_COMPRESSION_METHOD=zstd
```
Secure the environment directory:
```bash
chown -R postgres:postgres /etc/wal-g.d
chmod 600 /etc/wal-g.d/env
```

### Step 2: Configure PostgreSQL Archiving
Modify `/etc/postgresql/16/main/postgresql.conf`:
```ini
wal_level = replica
archive_mode = on
archive_command = 'envdir /etc/wal-g.d/env wal-g wal-push "%p"'
archive_timeout = 600  # Force WAL switch at least every 10 minutes
```
*Note: Using `envdir` is a standard way to expose environment files securely to commands executed by PostgreSQL.*

### Step 3: Reload PostgreSQL Configuration
```bash
sudo systemctl reload postgresql
```

### Step 4: Validate WAL Archiving
Verify that new WAL files are uploaded to S3:
```bash
# Force a WAL switch
sudo -u postgres psql -c "SELECT pg_switch_wal();"

# List WAL files from S3 to verify the upload
sudo -u postgres envdir /etc/wal-g.d/env wal-g wal-show
```

---

## Runbook 2: Daily Operations and Monitoring

### Step 1: Schedule Base Backups
Base backups must be scheduled periodically (e.g., daily) to limit the time needed to replay WAL files during recovery.
Create a cron job `/etc/cron.d/wal-g-backup`:
```cron
# Run daily base backup at 02:00 AM
0 2 * * * postgres envdir /etc/wal-g.d/env wal-g backup-push /var/lib/postgresql/16/main >> /var/log/postgresql/wal-g-backup.log 2>&1
```

### Step 2: Set Up Archive Monitoring
Monitor WAL archiving to ensure backups don't fall behind.
*   **Check Archiving Status in PostgreSQL:**
    ```sql
    SELECT * FROM pg_stat_archiver;
    ```
    Ensure `last_failed_time` is empty or older than `last_archived_time`.
*   **Alerting on Archiving Failures:**
    Write a cron monitor or export Prometheus metrics checking if the number of files in `pg_wal/archive_status/*.ready` exceeds a threshold (e.g., > 10 files). If it does, alert the team immediately as local disks could fill up.

---

## Runbook 3: Disaster Recovery: Full Database Restore

Use this runbook to restore a completely dead database server using the latest base backup.

### Step 1: Provision the Server
Ensure a new PostgreSQL instance is installed with the exact same major version and configuration.

### Step 2: Stop PostgreSQL Service
```bash
sudo systemctl stop postgresql
```

### Step 3: Clean Up Existing Data
> [!WARNING]
> This step is destructive. Ensure you are on the correct server before running.
```bash
sudo -u postgres rm -rf /var/lib/postgresql/16/main/*
```

### Step 4: Fetch the Base Backup
Download the latest base backup from S3:
```bash
sudo -u postgres envdir /etc/wal-g.d/env wal-g backup-fetch /var/lib/postgresql/16/main LATEST
```

### Step 5: Configure Recovery Signal
Create a recovery signal to tell PostgreSQL to enter archive recovery:
```bash
sudo -u postgres touch /var/lib/postgresql/16/main/recovery.signal
```

### Step 6: Configure Recovery Commands
Add the `restore_command` and target options to `postgresql.auto.conf`:
```bash
sudo -u postgres sh -c 'cat <<EOF >> /var/lib/postgresql/16/main/postgresql.auto.conf
restore_command = '\''envdir /etc/wal-g.d/env wal-g wal-fetch "%f" "%p"'\''
recovery_target_action = '\''promote'\''
EOF'
```

### Step 7: Start PostgreSQL and Monitor Logs
```bash
sudo systemctl start postgresql
sudo tail -f /var/log/postgresql/postgresql-16-main.log
```
Verify in the logs that:
1. PostgreSQL enters recovery mode.
2. It fetches and extracts the base backup.
3. It replays WAL logs via `wal-fetch`.
4. It finishes recovery, renames `recovery.signal` to `recovery.done`, and promotes itself to read-write.

---

## Runbook 4: Point-in-Time Recovery (PITR)

Use this runbook to restore the database to a specific point-in-time prior to an event (e.g., recovering from a `DROP TABLE` executed by mistake at `2026-07-16 10:45:00 UTC`).

### Step 1: Identify the Target Time
Retrieve the exact timestamp *just before* the disaster occurred.
*Target Recovery Time:* `2026-07-16 10:44:59 UTC`.

### Step 2: Stop PostgreSQL and Clean Data Directory
```bash
sudo systemctl stop postgresql
sudo -u postgres rm -rf /var/lib/postgresql/16/main/*
```

### Step 3: Fetch the Closest Prior Base Backup
Do not use `LATEST` if a backup was taken *after* the target recovery time. List the backups and pick the closest one prior to the target:
```bash
sudo -u postgres envdir /etc/wal-g.d/env wal-g backup-list
# Example output: base_000000010000000000000010 (created at 2026-07-16 02:00:00 UTC)

sudo -u postgres envdir /etc/wal-g.d/env wal-g backup-fetch /var/lib/postgresql/16/main base_000000010000000000000010
```

### Step 4: Configure Recovery Signal & Recovery Parameters
Create the recovery signal:
```bash
sudo -u postgres touch /var/lib/postgresql/16/main/recovery.signal
```
Configure target options in `postgresql.auto.conf`:
```bash
sudo -u postgres sh -c 'cat <<EOF >> /var/lib/postgresql/16/main/postgresql.auto.conf
restore_command = '\''envdir /etc/wal-g.d/env wal-g wal-fetch "%f" "%p"'\''
recovery_target_time = '\''2026-07-16 10:44:59 UTC'\''
recovery_target_action = '\''promote'\''
EOF'
```

### Step 5: Start PostgreSQL and Validate
```bash
sudo systemctl start postgresql
```
Monitor the logs. Once PostgreSQL promotes itself, log in and verify that the deleted database objects are restored and available.

---

## Runbook 5: Backup Lifecycle and Retention Policy Enforcement

To prevent infinite cloud storage accumulation, you must automate the pruning of old backups and WALs.

### Step 1: Choose a Retention Policy
A typical policy: **Retain backups for 14 days.**

### Step 2: Schedule Pruning
Create a daily cron job `/etc/cron.d/wal-g-cleanup`:
```cron
# Run backup cleanup daily at 03:00 AM
0 3 * * * postgres envdir /etc/wal-g.d/env wal-g delete retain FULL 14 --confirm >> /var/log/postgresql/wal-g-cleanup.log 2>&1
```
*Note: WAL-G will automatically identify the oldest retained backup, keep all WAL segments required to restore that backup (plus any newer ones), and safely delete all older base backups and redundant WAL logs.*

---

## Runbook 6: Security Hardening

Backups contain sensitive business data. Hardening the backup pipeline is critical.

### 1. Storage Encryption (Libsodium)
To protect backups from unauthorized access, encrypt them client-side before sending them to the cloud.

1.  **Generate a 32-byte secret key:**
    ```bash
    openssl rand -base64 32 > /etc/wal-g.d/libsodium.key
    chmod 600 /etc/wal-g.d/libsodium.key
    chown postgres:postgres /etc/wal-g.d/libsodium.key
    ```
2.  **Add the encryption parameters to `/etc/wal-g.d/env`:**
    ```ini
    WALG_LIBSODIUM_KEY_PATH=/etc/wal-g.d/libsodium.key
    ```
    *WAL-G will automatically detect this key, encrypt backups/WALs during `push` operations, and decrypt them during `fetch` operations.*

### 2. IAM Policy Least Privilege
If using AWS S3, do not use credentials with administrative access. Restrict permissions strictly to the target backup folder.

Example IAM Policy for the PostgreSQL server:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowWALGActions",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::my-prod-bucket",
                "arn:aws:s3:::my-prod-bucket/pg-backups/*"
            ]
        }
    ]
}
```

### 3. S3 Bucket Protection
*   **Enable Versioning**: Protect against accidental deletion of backups in the bucket.
*   **Object Lock (WORM)**: For compliance (e.g., PCI-DSS, HIPAA), enable S3 Object Lock in compliance mode with a retention duration (e.g., 30 days) to prevent any deletion of backups—even by compromised admin credentials—during the retention window.
*   **Server-Side Encryption (SSE)**: Force encryption at rest at the bucket level using KMS keys.
