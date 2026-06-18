DIST_DIR=dist
RPM_PYTHON_LIB_PATH=$(shell python3 -c "import sysconfig; print(sysconfig.get_path('purelib'))")
PROJECT := pkgbot

# Force the python3 package-name prefix so the package name does not depend on
# fpm seems to default to python-$pkg
DEB_PREFIX := --python-package-name-prefix python3

.PHONY: all-pkg deb rpm deb-python-gitlab rpm-python-gitlab clean

all-pkg: deb rpm deb-python-gitlab rpm-python-gitlab

$(DIST_DIR):
	mkdir -p $(DIST_DIR)

clean:
	rm $(DIST_DIR)/*

deb: $(DIST_DIR)
	fpm -s python -t deb $(DEB_PREFIX) --no-python-dependencies \
		-d expect \
		-d "python3-yaml | python-yaml" \
		-d "python3-requests | python-requests" \
		-d "python3-gitlab | python-gitlab" \
		--after-install pkgbot/scripts/pkg-mkdirs.sh setup.py
	mv python*-gitlab-pkgbot_*_all.deb $(DIST_DIR)

deb-python-gitlab: $(DIST_DIR)
	cd $(DIST_DIR) && fpm -s python -t deb $(DEB_PREFIX) python-gitlab

rpm: $(DIST_DIR)
	fpm -s python -t rpm -d expect -d PyYAML -d python-setuptools --after-install pkgbot/scripts/pkg-mkdirs.sh --python-install-lib $(RPM_PYTHON_LIB_PATH) setup.py
	mv python*-gitlab-pkgbot-*.noarch.rpm $(DIST_DIR)

rpm-python-gitlab: $(DIST_DIR)
	cd $(DIST_DIR) && fpm -s python -t rpm -d python-setuptools --python-install-lib $(RPM_PYTHON_LIB_PATH) python-gitlab
