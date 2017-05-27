# -*- coding: UTF-8 -*-

"""Setuptools package definition"""

from setuptools import setup
from setuptools import find_packages
import codecs
import sys
import os

version = sys.version_info[0]
if version > 2:
    pass
else:
    pass


__version__  = None
version_file = "pkgbot/version.py"
with codecs.open(version_file, encoding="UTF-8") as f:
    code = compile(f.read(), version_file, 'exec')
    exec(code)


def find_data(packages, extensions):
    """Finds data files along with source.

    :param   packages: Look in these packages
    :param extensions: Look for these extensions
    """
    data = {}
    for package in packages:
        package_path = package.replace('.', '/')
        for dirpath, _, filenames in os.walk(package_path):
            for filename in filenames:
                for extension in extensions:
                    if filename.endswith(".%s" % extension):
                        file_path = os.path.join(
                            dirpath,
                            filename
                        )
                        file_path = file_path[len(package) + 1:]
                        if package not in data:
                            data[package] = []
                        data[package].append(file_path)
    return data


with codecs.open('README.md', 'r', encoding="UTF-8") as f:
    README_TEXT = f.read()


setup(
    name = "gitlab-pkgbot",
    version = __version__,
    packages = find_packages(),
    package_data=find_data(
        find_packages(), ["py", "yaml", "service"]
    ),
    data_files = [
        ('/etc', ['pkgbot/config/gitlab-pkgbot.yaml']),
        ('/lib/systemd/system', [
            'pkgbot/config/gitlab-pkgbot.service',
            'pkgbot/config/aptly-spooler.service'
        ]),
        ('/usr/local/bin', ['pkgbot/scripts/rpmsign-nointeractive.sh'])
    ],
    entry_points = {
        'console_scripts': [
            'gitlab-pkgbot = pkgbot:main',
            'aptly-spooler = pkgbot.aptlyspooler:main'
        ]
    },
    install_requires = [
        "requests",
        # "pyyaml",
        "python-gitlab"
    ],
    author = "Adfinis SyGroup AG",
    author_email = "https://adfinis-sygroup.ch/",
    description = "GitLab CI Package Bot",
    long_description = README_TEXT,
    keywords = "GitLab CI pkgbot bot",
    url = "https://github.com/adfinis-sygroup/gitlab-pkgbot",
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.6",
        "Topic :: Software Development :: Build Tools"
    ]
)
