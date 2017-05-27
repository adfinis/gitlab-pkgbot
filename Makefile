DIST_DIR=dist
RPM_PYTHON_LIB_PATH=/usr/lib/python2.7/site-packages
PROJECT := pkgbot
GIT_HUB := https://github.com/adfinis-sygroup/gitlab-pkgbot

include pyproject/Makefile

all-pkg: deb rpm deb-python-gitlab rpm-python-gitlab

$(DIST_DIR):
	mkdir -p $(DIST_DIR)

clean:
	rm $(DIST_DIR)/*

deb: $(DIST_DIR)
	fpm -s python -t deb -d expect -d python-yaml --after-install pkgbot/scripts/pkg-mkdirs.sh setup.py
	mv python-gitlab-pkgbot_*_all.deb $(DIST_DIR)

deb-python-gitlab: $(DIST_DIR)
	cd $(DIST_DIR) && fpm -s python -t deb python-gitlab

rpm: $(DIST_DIR)
	fpm -s python -t rpm -d expect -d PyYAML -d python-setuptools --after-install pkgbot/scripts/pkg-mkdirs.sh --python-install-lib $(RPM_PYTHON_LIB_PATH) setup.py
	mv python-gitlab-pkgbot-*.noarch.rpm $(DIST_DIR)

rpm-python-gitlab: $(DIST_DIR)
	cd $(DIST_DIR) && fpm -s python -t rpm -d python-setuptools --python-install-lib $(RPM_PYTHON_LIB_PATH) python-gitlab
