
ARGS=target/test.uza

all: build

build:
	$(MAKE) -C src/vm

run: build
	# $(MAKE) -C src/vm/main
	./src/vm/main $(ARGS)

test: 
	$(MAKE) -C tests
	pytest

clean:
	$(MAKE) -C src/vm clean
	$(MAKE) -C tests clean

.PHONY: clean
