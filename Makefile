.PHONY: help build up down restart logs shell install upgrade test test-one lint e2e e2e-install clean

MODULE := pan_mcp_pro_governance
DEV_DB := dev
COMPOSE := docker-compose -f .local/docker-compose.yml

help:
	@echo "Targets:"
	@echo "  build       Rebuild the Odoo image (when Dockerfile or odoo-enterprise changes)"
	@echo "  up          Start Odoo + Postgres in background"
	@echo "  down        Stop and remove containers"
	@echo "  restart     Restart Odoo (rare with --dev=all)"
	@echo "  logs        Tail Odoo logs"
	@echo "  shell       Exec bash inside the Odoo container"
	@echo "  install     Install the module on a fresh dev DB"
	@echo "  upgrade     Apply schema/manifest changes (-u $(MODULE))"
	@echo "  test        Fresh DB + install + run all module tests (CI-style)"
	@echo "  test-one    TAG=:Class.method  Run a single test"
	@echo "  lint        Run pre-commit on all files"
	@echo "  e2e-install Install Playwright deps (one-time)"
	@echo "  e2e         Run Playwright suite (screenshot capture)"
	@echo "  clean       Drop test_* databases"

build:
	$(COMPOSE) build odoo

up:
	$(COMPOSE) up -d
	@echo "Odoo: http://localhost:8069 (db: $(DEV_DB), admin/admin)"

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart odoo

logs:
	$(COMPOSE) logs -f odoo

shell:
	$(COMPOSE) exec odoo bash

install:
	$(COMPOSE) stop odoo
	$(COMPOSE) run --rm odoo python -m odoo \
		-c /etc/odoo/odoo.conf -d $(DEV_DB) \
		-i $(MODULE) --stop-after-init --without-demo=True
	$(COMPOSE) start odoo

upgrade:
	$(COMPOSE) stop odoo
	$(COMPOSE) run --rm odoo python -m odoo \
		-c /etc/odoo/odoo.conf -d $(DEV_DB) \
		-u $(MODULE) --stop-after-init
	$(COMPOSE) start odoo

# Fresh-DB install + tests on an ephemeral DB.
# This is the canonical "would the App Store reviewer's install succeed?" guard.
# Uses `run --rm` (not `exec`) so the test process gets its own container with
# its own port bindings — main Odoo keeps running for browser iteration.
test:
	@TESTDB=test_$$(date +%s); \
	echo "Test DB: $$TESTDB"; \
	$(COMPOSE) stop odoo; \
	$(COMPOSE) run --rm odoo python -m odoo \
		-c /etc/odoo/odoo.conf -d $$TESTDB \
		-i $(MODULE) \
		--test-enable --test-tags=/$(MODULE) \
		--stop-after-init --without-demo=True; \
	RC=$$?; \
	$(COMPOSE) exec -T db dropdb -U odoo --if-exists $$TESTDB; \
	$(COMPOSE) start odoo; \
	exit $$RC

# Run a single test. Example: make test-one TAG=:TestApiCallLog.test_audit_log_correlation
test-one:
	@if [ -z "$(TAG)" ]; then echo "Usage: make test-one TAG=:Class.method"; exit 1; fi
	@TESTDB=test_one_$$(date +%s); \
	echo "Test DB: $$TESTDB  Tag: /$(MODULE)$(TAG)"; \
	$(COMPOSE) stop odoo; \
	$(COMPOSE) run --rm odoo python -m odoo \
		-c /etc/odoo/odoo.conf -d $$TESTDB \
		-i $(MODULE) \
		--test-enable --test-tags=/$(MODULE)$(TAG) \
		--stop-after-init --without-demo=True; \
	RC=$$?; \
	$(COMPOSE) exec -T db dropdb -U odoo --if-exists $$TESTDB; \
	$(COMPOSE) start odoo; \
	exit $$RC

lint:
	pre-commit run --all-files

e2e-install:
	cd .local/playwright && npm install && npx playwright install chromium

e2e:
	cd .local/playwright && npx playwright test

# Drop all DBs starting with test_ — useful after killing test runs partway.
clean:
	@$(COMPOSE) exec -T db psql -U odoo -d postgres -tAc \
		"SELECT datname FROM pg_database WHERE datname LIKE 'test_%';" \
		| xargs -I {} $(COMPOSE) exec -T db dropdb -U odoo --if-exists {}
