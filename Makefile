
ARGS=target/test.uza

DEBUG ?= 1

all: build

build:
	mkdir -p ./target
	$(MAKE) -C src/vm

test_build: clean
	$(MAKE) -C src/vm DEBUG=0

prun: build
	pypy3 ./src/main.py

run: build
	# $(MAKE) -C src/vm/main DEBUG=$(DEBUG)
	./src/vm/main $(ARGS)

crun: clean build
	./src/vm/main $(ARGS)

test: test_build
	# $(MAKE) -C test
	pypy3 -m pytest

clean:
	$(MAKE) -C src/vm/ clean
	$(MAKE) -C test clean

.PHONY: clean test
