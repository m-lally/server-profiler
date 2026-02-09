.PHONY: install setup test profile clean help

help:
	@echo "Server Profiler - Makefile Commands"
	@echo "===================================="
	@echo "install     - Install dependencies"
	@echo "setup       - Initial setup (install + permissions)"
	@echo "profile     - Run profiler with default Lightsail config"
	@echo "clean       - Clean generated files"
	@echo "test        - Run tests"
	@echo ""
	@echo "Usage examples:"
	@echo "  make install"
	@echo "  make profile HOST=example.com USER=admin KEY=~/.ssh/key.pem"

install:
	pip install -r requirements.txt

setup: install
	chmod +x profiler.py
	@echo "✓ Setup complete"

# Profile server with Lightsail config
profile-lightsail:
	@if [ -z "$(INSTANCE)" ]; then \
		echo "Error: INSTANCE name required"; \
		echo "Usage: make profile-lightsail INSTANCE=my-server"; \
		exit 1; \
	fi
	python profiler.py \
		--lightsail-config ~/.ssh/lightsail-ssh-config \
		--instance-name $(INSTANCE) \
		--terraform

# Profile server with direct connection
profile:
	@if [ -z "$(HOST)" ] || [ -z "$(KEY)" ]; then \
		echo "Error: HOST and KEY required"; \
		echo "Usage: make profile HOST=example.com KEY=~/.ssh/key.pem [USER=admin]"; \
		exit 1; \
	fi
	python profiler.py \
		--host $(HOST) \
		--user $(or $(USER),admin) \
		--key $(KEY) \
		--terraform

# Quick profile without Terraform
quick-profile:
	@if [ -z "$(HOST)" ] || [ -z "$(KEY)" ]; then \
		echo "Error: HOST and KEY required"; \
		exit 1; \
	fi
	python profiler.py \
		--host $(HOST) \
		--user $(or $(USER),admin) \
		--key $(KEY) \
		--no-terraform

clean:
	rm -f profile.json
	rm -rf terraform/
	rm -rf __pycache__/
	rm -rf *.pyc
	@echo "✓ Cleaned generated files"

test:
	python -m pytest tests/ -v

# Docker support (optional)
docker-build:
	docker build -t server-profiler .

docker-run:
	docker run -it --rm \
		-v ~/.ssh:/root/.ssh:ro \
		-v $(PWD)/output:/app/output \
		server-profiler
