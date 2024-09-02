
ARGS=target/test.uza

all: build

build:
	$(MAKE) -C src/vm

test_build: clean
	$(MAKE) -C src/vm DEBUG=0

run: build
	# $(MAKE) -C src/vm/main
	./src/vm/main $(ARGS)

crun: clean build
	./src/vm/main $(ARGS)

test: test_build
	# $(MAKE) -C tests
	pypy3 -m pytest

clean:
	$(MAKE) -C src/vm clean
	$(MAKE) -C tests clean

.PHONY: clean test
