# Apple Vision / Core Image helpers (arm64). `make` rebuilds any binary older than its source.
# face = head pose, pupils, mouth, smile + Core Image blink / smile classifiers (thumbs.py); facequality = largest face box + capture quality (hook overlay side).
SWIFTC ?= swiftc
BIN = facequality face
all: $(BIN)
%: %.swift
	$(SWIFTC) -O -o $@ $< -framework Vision -framework AppKit -framework CoreImage
clean:
	rm -f $(BIN)
.PHONY: all clean
