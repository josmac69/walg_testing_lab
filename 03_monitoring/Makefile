.PHONY: up down init-db backup add-data status

up:
	docker compose up -d --build
	@echo "Waiting for services to be ready..."
	@until docker compose exec postgres pg_isready -h localhost -U postgres >/dev/null 2>&1; do \
		sleep 1; \
	done
	@echo "Services are up and running."
	@echo "Grafana is running on http://localhost:3000 (Credentials: admin/admin)"
	@echo "Prometheus is running on http://localhost:9090"

down:
	docker compose down -v

init-db:
	@echo "Initializing database schema and seeding data..."
	docker compose exec -T postgres psql -U postgres -d walg_test -f /sql/01_init.sql
	@echo "Database seeded successfully."
	@docker compose exec -T postgres psql -U postgres -d walg_test -c "SELECT * FROM inventory;"

backup:
	@echo "Creating WAL-G base backup..."
	docker compose exec -T --user postgres postgres wal-g backup-push /var/lib/postgresql/data/pgdata
	@echo "Base backup completed and pushed to MinIO."

add-data:
	@echo "Inserting post-backup records..."
	docker compose exec -T postgres psql -U postgres -d walg_test -f /sql/02_insert.sql
	@echo "Flushing current WAL segment to ensure archiving is triggered..."
	docker compose exec -T postgres psql -U postgres -d walg_test -c "SELECT pg_switch_wal();"
	@docker compose exec -T postgres psql -U postgres -d walg_test -c "SELECT * FROM inventory;"

status:
	@echo "=== Exporter Metrics ==="
	@curl -s http://localhost:9351/metrics
