SHELL := /bin/bash
APP  := quickdcp-api
REG  := ams
PORT := 8080

.PHONY: help infra tf fmt plan apply destroy build run dev worker demo sbom sign deploy secrets logs clean verify serve compose compose-down

help:
	@echo "Targets: infra tf plan apply destroy build run dev worker demo sbom sign deploy secrets logs clean verify serve compose compose-down"

# --- Terraform ---
infra: tf

tf:
	cd infra/terraform && terraform init

fmt:
	cd infra/terraform && terraform fmt -recursive

plan:
	cd infra/terraform && terraform plan -var="aws_region=eu-central-1" -var="project=quickdcp" -var="budget_usd=150"

apply:
	cd infra/terraform && terraform apply -auto-approve -var="aws_region=eu-central-1" -var="project=quickdcp" -var="budget_usd=150"

destroy:
	cd infra/terraform && terraform destroy -auto-approve

# --- Build & Run ---
build:
	docker build -t $(APP):latest -f infra/Dockerfile .

run:
	UVICORN_WORKERS=1 docker run --rm -e PORT=$(PORT) -p $(PORT):$(PORT) $(APP):latest

# --- Local Dev ---
dev:
	UVICORN_WORKERS=1 uvicorn api.main:app --host 0.0.0.0 --port $(PORT)

worker:
	API_BASE=http://localhost:$(PORT) WORKER_TOKEN=dev-worker-token python3 worker/worker.py

# --- Demo (local TSA mock + proof roundtrip) ---
demo:
	set -e; \
	curl -s -X POST localhost:$(PORT)/jobs/render -H 'Content-Type: application/json' -d '{"job_id":"JOB-DEMO","profile":{"res":"2K"}}' >/dev/null; \
	python3 worker/worker.py & sleep 2; \
	curl -s -X POST localhost:$(PORT)/proof/init -H 'X-QD-Customer: demo' -H 'Authorization: QuickDCP demo' -H 'Content-Type: application/json' -d '{"job_id":"JOB-DEMO"}' > /tmp/pi.json; \
	SHA=$$(jq -r '.manifest_sha256' /tmp/pi.json); \
	./ops/tsa_mock.sh $$SHA; \
	TSR_B64=$$(base64 -w0 resp.tsr); \
	curl -s -X POST localhost:$(PORT)/proof/ack/tsa -H 'X-QD-Customer: demo' -H 'Authorization: QuickDCP demo' -H 'Content-Type: application/json' -d '{"job_id":"JOB-DEMO","tsr_base64":"'"$$TSR_B64"'"}' | jq

# --- SBOM + Sign (requires syft & cosign) ---
sbom:
	pipx run syft . -o spdx-json > vault/sbom.spdx.json || (pip install syft && syft . -o spdx-json > vault/sbom.spdx.json)

sign:
	cosign sign --yes $(APP):latest || true

# --- Fly deploy ---
deploy:
	flyctl deploy -c infra/fly.toml --remote-only

secrets:
	@echo "Use: flyctl secrets set KEY=VALUE ..."

logs:
	flyctl logs -a $(APP)

# --- Utils ---
verify:
	bash ops/verify_offline.sh

serve:
	python3 -m http.server 8088 -d public

compose:
	docker compose up --build

compose-down:
	docker compose down -v

clean:
	rm -f resp.tsr req.tsq /tmp/pi.json
