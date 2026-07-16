# Lab 02: Encrypted & Compressed Backups with Libsodium & Zstandard

This lab demonstrates how to secure database backups and optimize storage by configuring **WAL-G** to perform client-side **symmetric encryption** using **Libsodium** and **high-performance compression** using **Zstandard (zstd)**.

---

## Why Libsodium & Zstandard?

1. **Libsodium Symmetric Encryption**:
   - Historically, WAL-G (and WAL-E) used GnuPG (GPG) for encryption. However, PGP/GPG key management is complex, error-prone, and now deprecated in WAL-G.
   - Libsodium uses a single 32-byte key, which is significantly faster to process, highly secure, and extremely simple to configure using environment variables.
   
2. **Zstandard Compression**:
   - Zstandard (`zstd`) is a real-time compression algorithm developed by Meta.
   - It provides compression ratios comparable to gzip but at CPU speeds closer to lz4, making it the default recommendation for heavy database backup workloads.

---

## Configuration & Key Management

### Encryption Key Generation
Before starting the containers, we generate a cryptographically secure 32-byte key using `openssl`:
```bash
openssl rand -base64 32
```
This is automatically handled by the Makefile and written to a local `.env` file, which is then loaded by Docker Compose.

### WAL-G Security Parameters
The following settings are passed in the environment to instruct WAL-G to encrypt and compress all uploaded payloads (both basebackups and WAL segments):
- `WALG_COMPRESSION_METHOD: zstd`: Compresses files using Zstandard.
- `WALG_LIBSODIUM_KEY: <base64 key>`: Secret key used to encrypt the payload.
- `WALG_LIBSODIUM_KEY_TRANSFORM: base64`: Tells WAL-G that the key is encoded in Base64 (so it will decode it to binary internally).

During `backup-push` and `wal-push`, WAL-G compresses the files, encrypts the compressed bytes using Libsodium, and then writes them to S3.
During `backup-fetch` and `wal-fetch`, WAL-G retrieves the encrypted files, decrypts them using the key, decompresses them, and restores them.

---

## Step-by-Step Execution Guide

### 1. Launch the Lab
Run setup and spin up the containers:
```bash
make up
```
This will:
- Check for `.env` and automatically generate a new Libsodium key if it does not exist.
- Start PostgreSQL, MinIO, and create the `walg-backups` bucket.

### 2. Initialize the Database
Seed the database with sensitive tables and initial records:
```bash
make init-db
```
This runs `sql/01_init.sql` to populate an database table called `secure_data`.

### 3. Trigger an Encrypted Backup
Instruct WAL-G to back up the database:
```bash
make backup
```
If you inspect the files inside the MinIO bucket using the web console at [http://localhost:9001](http://localhost:9001), you will find that the uploaded files are compressed and fully encrypted. Without the Libsodium key, they cannot be read or unpacked.

### 4. Insert More Sensitive Transactions
Insert additional records and switch the active WAL log:
```bash
make add-data
```
This runs `sql/02_insert.sql` to write more records, forces a WAL rotation to archive them immediately, and saves the recovery target timestamp to `restore_time.txt`.

### 5. Simulate a Disaster
Drop the sensitive data table:
```bash
make disaster
```

### 6. Restore and Decrypt
Restore the database up to the point just before the disaster:
```bash
make restore
```
During this process, WAL-G reads `WALG_LIBSODIUM_KEY` from the environment, decrypts the basebackup, writes the `recovery.signal` file, and configures PostgreSQL to run `wal-g wal-fetch` for WAL retrieval (which also uses the Libsodium key to decrypt files on the fly during replay).

### 7. Verify Recovery
Check the database to verify the decrypted data:
```bash
make verify
```
You should see all 5 secret records successfully restored and decrypted.

### 8. Cleanup
To stop containers, remove volumes, and delete the generated key and environment files:
```bash
make down
```
