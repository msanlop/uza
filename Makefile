
all: build

build:
	$(MAKE) -C src/vm

test: 
	$(MAKE) -C tests
	pytest

clean:
	$(MAKE) -C src/vm clean
	$(MAKE) -C tests clean

.PHONY: clean
