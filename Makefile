.PHONY: up down logs rebuild refresh curl-search curl-ask help

DC ?= docker compose
API_BASE ?= http://localhost:8080
INGEST_BASE ?= http://localhost:8081

help:
	@echo "Targets:"
	@echo "  make up           - docker compose up -d --build"
	@echo "  make down         - docker compose down"
	@echo "  make logs         - docker compose logs -f"
	@echo "  make rebuild      - docker compose build --no-cache"
	@echo "  make refresh      - trigger ingest pipeline"
	@echo "  make curl-search  - test /search"
	@echo "  make curl-ask     - test /ask"

up:
	$(DC) up -d 
	docker exec -it vilaw-ollama-1 ollama pull qwen2.5:7b

down:
	$(DC) down

logs:
	$(DC) logs -f

rebuild:
	$(DC) build --no-cache

# Enqueue pipeline full (download -> parse -> chunk -> embed -> index)
refresh:
	curl -X POST $(INGEST_BASE)/ingest/refresh

curl-search:
	curl -s -X POST $(API_BASE)/search -H 'Content-Type: application/json' -d '{"q":"Điều kiện cấp phép quảng cáo rượu","top_k":5}' | jq

curl-ask:
	curl -s -X POST $(API_BASE)/ask -H 'Content-Type: application/json' -d '{"q":"Khi nào được quảng cáo rượu bia?","top_k":6}' | jq
