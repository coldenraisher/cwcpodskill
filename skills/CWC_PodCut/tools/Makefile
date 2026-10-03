# Apple Vision / CoreImage helpers (arm64). `make` rebuilds a binary when its source is newer.
SWIFTC ?= swiftc
all: expr textcount
expr: expr.swift
	$(SWIFTC) -O -o $@ $< -framework Vision -framework CoreImage
textcount: textcount.swift
	$(SWIFTC) -O -o $@ $< -framework Vision
clean:
	rm -f expr textcount
.PHONY: all clean
