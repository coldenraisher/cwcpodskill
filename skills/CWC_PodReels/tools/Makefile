# Apple Vision helpers (arm64). `make` rebuilds any binary older than its source.
SWIFTC ?= swiftc
BIN = facequality mouth face ocr
all: $(BIN)
%: %.swift
	$(SWIFTC) -O -o $@ $< -framework Vision -framework AppKit
clean:
	rm -f $(BIN)
.PHONY: all clean
