# Makefile for common development tasks
.PHONY: help migrate run dev shell

help:
	@echo "Makefile targets:"
	@echo "  migrate   - run django migrations"
	@echo "  run       - run the development server (requires migrations already applied)"
	@echo "  dev       - apply migrations then runserver (useful for local dev)"
	@echo "  shell     - open django shell"

migrate:
	python3 manage.py migrate

run:
	python3 manage.py runserver

dev: migrate
	@echo "Starting development server (after migrations)..."
	python3 manage.py runserver

shell:
	python3 manage.py shell
