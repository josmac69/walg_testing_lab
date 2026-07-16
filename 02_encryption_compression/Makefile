.PHONY: help setup-env up down init-db backup add-data disaster restore verify

help:
	@echo "Available commands:"
	@echo "  make up             - Set up env key, build and start PostgreSQL and MinIO"
	@echo "  make down           - Stop containers and remove volumes & .env files"
	@echo "  make init-db        - Create schema and insert initial sensitive data"
	@echo "  make backup         - Perform WAL-G basebackup (encrypted & compressed)"
	@echo "  make add-data       - Insert post-backup records, flush WAL, and save timestamp"
	@echo "  make disaster       - Drop the secure_data table to simulate data loss"
	@echo "  make restore        - Perform PITR restore (auto-decrypts using Libsodium key)"
	@echo "  make verify         - Verify that the decrypted data is correctly restored"

setup-env:
	@if [ ! -f .env ]; then \
		echo "Generating 32-byte Libsodium symmetric key..."; \
		echo "WALG_LIBSODIUM_KEY=$$(openssl rand -base64 32)" > .env; \
		echo "Encryption key generated in .env file."; \
	fi

up: setup-env
	docker compose up -d --build
	@echo "Waiting for services to be ready..."
	@sleep 5
	@until docker compose exec postgres pg_isready -U postgres -d walg_encrypt_test; do echo "Waiting for PostgreSQL..."; sleep 2; done
	@echo "Services are up and running."

down:
	docker compose down -v
	rm -f .env
	rm -f restore_time.txt

init-db:
	@echo "Initializing database schema and seeding data..."
	docker compose exec -T postgres psql -U postgres -d walg_encrypt_test -f /sql/01_init.sql
	@echo "Database seeded successfully."
	@docker compose exec -T postgres psql -U postgres -d walg_encrypt_test -c "SELECT * FROM secure_data;"

backup:
	@echo "Creating WAL-G encrypted & compressed base backup..."
	docker compose exec -T --user postgres postgres wal-g backup-push /var/lib/postgresql/data/pgdata
	@echo "Base backup completed and pushed to MinIO."

add-data:
	@echo "Inserting post-backup records..."
	docker compose exec -T postgres psql -U postgres -d walg_encrypt_test -f /sql/02_insert.sql
	@echo "Flushing current WAL segment to ensure archiving is triggered..."
	docker compose exec -T postgres psql -U postgres -d walg_encrypt_test -c "SELECT pg_switch_wal();"
	@echo "Saving the target recovery timestamp..."
	docker compose exec -T postgres psql -U postgres -d walg_encrypt_test -t -A -c "SELECT current_timestamp;" > restore_time.txt
	@echo "Recovery target time saved: $$(cat restore_time.txt)"
	@docker compose exec -T postgres psql -U postgres -d walg_encrypt_test -c "SELECT * FROM secure_data;"

disaster:
	@echo "Simulating disaster: dropping 'secure_data' table..."
	docker compose exec -T postgres psql -U postgres -d walg_encrypt_test -c "DROP TABLE secure_data;"
	@echo "Disaster completed. Table dropped."

restore:
	@if [ ! -f restore_time.txt ]; then echo "Error: restore_time.txt not found. Execute 'make add-data' first."; exit 1; fi
	@echo "Stopping PostgreSQL server to prepare for recovery..."
	docker compose stop postgres
	@echo "Cleaning up the current data directory..."
	docker compose run --user postgres --rm --entrypoint="" postgres sh -c "rm -rf /var/lib/postgresql/data/pgdata/*"
	@echo "Fetching and decrypting the base backup via WAL-G..."
	docker compose run --user postgres --rm --entrypoint="" postgres wal-g backup-fetch /var/lib/postgresql/data/pgdata LATEST
	@echo "Creating recovery.signal file..."
	docker compose run --user postgres --rm --entrypoint="" postgres touch /var/lib/postgresql/data/pgdata/recovery.signal
	@echo "Configuring recovery target parameters in postgresql.auto.conf..."
	@RESTORE_TIME=$$(cat restore_time.txt); \
	docker compose run --user postgres --rm --entrypoint="" postgres sh -c "\
		echo \"restore_command = 'wal-g wal-fetch \\\"%f\\\" \\\"%p\\\"'\" >> /var/lib/postgresql/data/pgdata/postgresql.auto.conf && \
		echo \"recovery_target_time = '$$RESTORE_TIME'\" >> /var/lib/postgresql/data/pgdata/postgresql.auto.conf && \
		echo \"recovery_target_action = 'promote'\" >> /var/lib/postgresql/data/pgdata/postgresql.auto.conf \
	"
	@echo "Starting PostgreSQL in recovery mode..."
	docker compose start postgres
	@echo "Waiting for recovery to complete and PostgreSQL to become ready..."
	@sleep 3
	@until docker compose exec postgres pg_isready -U postgres -d walg_encrypt_test; do echo "Waiting for PostgreSQL..."; sleep 2; done
	@echo "Recovery complete. PostgreSQL is ready."

verify:
	@echo "Querying secure_data table to verify PITR status..."
	docker compose exec -T postgres psql -U postgres -d walg_encrypt_test -c "SELECT * FROM secure_data;"
