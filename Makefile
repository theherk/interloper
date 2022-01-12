.DEFAULT_GOAL := help

NAME=interloper
VERSION=$$(git describe --tags --always)
PKG=build/lambda.zip

help: ## show help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m\033[0m\n"} /^[$$()% a-zA-Z./_-]+:.*?##/ { printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

clean: ## remove the build folder and built distribution
	rm -rf ./build

build:
	mkdir $@

build/%.zip: build ## create the distribution
	cp -r ./*.py ./build
	chmod 644 ./build/*.py
	pip install --target  ./build -r requirements.txt
	cd build && zip -r ./$(@F) .

.PHONY: dist
dist: $(PKG) ## create the distribution as build/lambda.zip

.PHONY: test
test: ## execute python tests
	python -m unittest

version: ## outpute the version
	@echo ${VERSION}
