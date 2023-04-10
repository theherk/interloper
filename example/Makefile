.DEFAULT_GOAL := help

OS := linux
ifeq (${shell uname},Darwin)
	OS := darwin
endif
ARCH := amd64
PKG := dist/lambda.zip

help: ## show help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m\033[0m\n"} /^[$$()% a-zA-Z./_-]+:.*?##/ { printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

clean: ## Clean up build artifacts.
	rm -rf __pycache__
	rm -rf dist
	rm -rf build

deps: ## install dependencies for development
ifeq (${OS},linux)
	if [ -n "$$(command -v yum)" ]; then \
		yum -y install curl gzip jq python3-pip tar unzip; \
	elif [ -n "$$(command -v apt)" ]; then \
		apt -y install curl jq unzip; \
		if [ $$(cat /etc/lsb-release | grep REL | cut -d "=" -f 2 | cut -d . -f1) -lt 20 ]; then \
			apt install -y python3.7 python3-pip; \
		else \
			apt install -y python3 python3-pip; \
		fi; \
	fi; \
	python3 -m pip install --upgrade pip
else ifeq (${OS},darwin)
	if [ -n "$$(command -v brew)" ]; then brew install coreutils jq; else echo "brew required"; fi
endif

.PHONY: dist
dist: $(PKG) ## create the distribution as dist/lambda.zip

dist/%.zip:
	mkdir -p dist
	pip install --target  ./build -r requirements.txt
	cp -r ./*.py ./build
	cp example.py interloper.sh ./build
	chmod 644 ./build/example.py ./build/interloper.sh
	rm -rf ./build/boto*
	cd build && zip -r ./$(@F) .
	mv build/$(@F) $@
