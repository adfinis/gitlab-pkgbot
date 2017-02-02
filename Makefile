all: deb rpm deb-python-gitlab rpm-python-gitlab deb-collect rpm-collect

deb:
	python setup.py --command-packages=stdeb.command bdist_deb

deb-clean:
	rm deb_dist/*
	rm dist/*
	rm gitlab-pkgbot-*.tar.gz

deb-python-gitlab:
	git clone https://github.com/gpocentek/python-gitlab
	cd python-gitlab && python setup.py --command-packages=stdeb.command sdist_dsc --package python-gitlab
	cd python-gitlab/deb_dist/python-gitlab-* && dpkg-buildpackage -rfakeroot -uc -us

deb-collect:
	mkdir -p dist/
	cp deb_dist/python-gitlab-pkgbot*deb dist
	cp python-gitlab/deb_dist/python-gitlab*.deb dist

rpm:
	python setup.py bdist --formats=rpm

rpm-python-gitlab:
	cd python-gitlab && python setup.py bdist --formats=rpm

rpm-collect:
	cp python-gitlab/dist/python-gitlab-*.rpm dist
