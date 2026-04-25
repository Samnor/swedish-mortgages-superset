up:
	python3 scripts/render_datasources.py
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f superset

import-datasources:
	python3 scripts/render_datasources.py
	docker compose exec superset superset import_datasources -p /app/codex_assets/datasources/swedish_mortgages.yaml -u $${SUPERSET_ADMIN_USERNAME:-admin}

bootstrap-dashboard:
	docker compose exec superset python /app/codex_assets/custom/create_mortgage_dashboard.py
