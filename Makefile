.PHONY: all-pkg package snapshot clean

NFPM_VERSION ?= v2.46.3
NFPM ?= go run github.com/goreleaser/nfpm/v2/cmd/nfpm@$(NFPM_VERSION)
PKGBOT_BASE_VERSION := $(shell git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo 0.0.0)
PKGBOT_COMMIT := $(shell git rev-parse --short=7 HEAD)
PKGBOT_DIRTY := $(shell test -z "$$(git status --porcelain)" || echo "-dirty")
PKGBOT_VERSION ?= $(PKGBOT_BASE_VERSION)-SNAPSHOT-$(PKGBOT_COMMIT)$(PKGBOT_DIRTY)

# Build the deb/rpm packages locally without publishing a release.
all-pkg: snapshot
package: snapshot

snapshot:
	rm -rf dist build/package-root build/wheel
	mkdir -p dist
	packaging/build-package-tree.sh --version "$(PKGBOT_VERSION)"
	PKGBOT_VERSION="$(PKGBOT_VERSION)" $(NFPM) pkg --config nfpm.yaml --packager deb --target dist/
	PKGBOT_VERSION="$(PKGBOT_VERSION)" $(NFPM) pkg --config nfpm.yaml --packager rpm --target dist/

clean:
	rm -rf build dist *.egg-info
