# By the Book — Docker helpers. On Windows without make, use the docker compose commands in the README.

.PHONY: help build up down dev logs clean migrate superuser reminders

help:
	@echo "Available commands:"
	@echo "  make build     - Build all Docker images"
	@echo "  make up        - Start production containers"
	@echo "  make dev       - Start development containers (Vite + Django autoreload)"
	@echo "  make down      - Stop all containers"
	@echo "  make logs      - Show logs from all containers"
	@echo "  make clean     - Remove all containers and volumes"
	@echo "  make migrate   - Run database migrations"
	@echo "  make superuser - Create a Django superuser"
	@echo "  make reminders - Email due reminders"

COMPOSE_PROD = docker compose -f docker-compose.yml

build:
	$(COMPOSE_PROD) build backend frontend

up:
	$(COMPOSE_PROD) up -d

dev:
	docker compose -f docker-compose.dev.yml up -d

down:
	$(COMPOSE_PROD) down
	docker compose -f docker-compose.dev.yml down

logs:
	docker compose -f docker-compose.dev.yml logs -f

clean:
	$(COMPOSE_PROD) down -v --remove-orphans
	docker compose -f docker-compose.dev.yml down -v --remove-orphans

migrate:
	$(COMPOSE_PROD) exec backend python manage.py migrate

superuser:
	$(COMPOSE_PROD) exec backend python manage.py createsuperuser

reminders:
	docker compose -f docker-compose.dev.yml exec backend python manage.py send_reminders

dev-migrate:
	docker compose -f docker-compose.dev.yml exec backend python manage.py migrate

dev-superuser:
	docker compose -f docker-compose.dev.yml exec backend python manage.py createsuperuser
