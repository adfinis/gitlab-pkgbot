#!/usr/bin/env python2
# -*- coding: utf-8 -*-


import requests
import logging
import time
import threading
import yaml
import json
import os
import sys
import tempfile
import shutil
import stat
import glob
import subprocess
from pkgbot.version import __version__

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from GitlabHelper import GitlabArtifactsDownloader


# init logging
def get_logger(prefix="adsy-pkgbot", project=False):
    loggername = prefix
    if project:
        loggername = "{0} - {1}".format(prefix, project)
    logger = logging.getLogger(loggername)
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s '
                                      '- %(message)s')
    ch = logging.StreamHandler()
    ch.setFormatter(log_formatter)
    logger.setLevel(20)
    logger.addHandler(ch)
    return logger


logger = get_logger()


def process_request(data):
    """
    Function to process an request from GitLab
    """

    global conf
    repo = "/".join(data['repository']['homepage'].split("/")[3:])
    logger.info("{0} - Process build trigger".format(repo))
    requests.packages.urllib3.disable_warnings()

    git = GitlabArtifactsDownloader(
        conf['gitlab']['url'],
        conf['gitlab']['token']
    )

    # check .pkg-bot.yml
    # TODO: better error checking
    try:
        repo_conf_dl   = git.download_raw_file(
            ".pkg-bot.yml",
            data['project_id'],
            data['ref']
        )
        rc             = yaml.load(repo_conf_dl.text)
        repo_conf      = rc['pkgbot']
    except:
        logger.error("{0} - Config for repo not found or invalid".format(repo))
        return

    # .pkg-bot.yml is dict-type
    if isinstance(repo_conf, dict):
        try:
            pkg_data       = repo_conf['packages']
            valid_branches = repo_conf['branches']
            wanted_repo    = repo_conf['repo']
        except:
            logger.error("{0} - Config for repo not found or invalid".format(
                repo))
            return

    # .pkg-bot.yml is list-type, find actual block
    elif isinstance(repo_conf, list):
        block_match = {}
        branches = []
        has_duplicate = False
        duplicate_branch_name = ""
        # search for duplicates
        for block in repo_conf:
            if 'branches' not in block:
                continue
            for branch in block['branches']:
                if data['ref'] == branch:
                    block_match = block
                if branch in branches:
                    has_duplicate = True
                    duplicate_branch_name = branch
                branches.append(branch)

        if not block_match:
            logger.error("{0} - No block in .pkg-bot.yml matches to branch "
                         "'{1}'".format(
                             repo,
                             data['ref']
                         ))
            return

        if has_duplicate:
            logger.error("{0} - Multiple matches for branch: {1} found".
                         format(
                             repo,
                             duplicate_branch_name
                         ))
            return

        repo_conf = block_match
        try:
            pkg_data       = repo_conf['packages']
            valid_branches = repo_conf['branches']
            wanted_repo    = repo_conf['repo']
        except:
            logger.error("{0} - Config for repo not found or invalid".format(
                repo))
            return

    # unknown .pkgbot.yml
    else:
        logger.error("{0} - Cannot parse .pkg-bot.yml".format(repo))
        return

    # check if we can write to aptly queue or fail
    fifo_socket_location = conf['pkgbot']['aptly-fifo-queue']
    has_sock = False
    try:
        has_sock = stat.S_ISFIFO(os.stat(fifo_socket_location).st_mode)
    except OSError:
        has_sock = False
    if not os.access(fifo_socket_location, os.W_OK):
        has_sock = False
    if not has_sock:
        logger.error("{0} - Cannot connect to aptly-spooler, socket: "
                     "{1}".format(
                         repo,
                         fifo_socket_location
                     ))
        return
    fifo = os.open(fifo_socket_location, os.O_NONBLOCK | os.O_WRONLY)

    # check if wanted repo exists and fail if not
    incoming_pkg_dir = "{0}/{1}".format(
        conf['pkgbot']['base-package-path'],
        wanted_repo
    )

    if not os.path.isdir(incoming_pkg_dir):
        logger.error("{0} - Directory for repo '{1}' not found".format(
            repo,
            incoming_pkg_dir
        ))
        return

    # branch is also required in config
    if data['ref'] not in valid_branches:
        logger.info("{0} - Branch: {1} does not match any configured".format(
            repo,
            data['ref']
        ))
        return

    # stages are optional
    if 'stages' in repo_conf:
        if data['build_stage'] not in repo_conf['stages']:
            logger.info("{0} - Build stage {1} does not match any "
                        "configured".format(
                            repo,
                            data['build_stage']
                        ))
            return

    # gitlab ci will trigger an build done event and then start to upload the
    # artifacts. users can configure an delay before downloading artifacts
    if 'download-delay' in repo_conf:
        logger.info("{0} - Config has delay in it, sleep for {1} secs".format(
            repo,
            repo_conf['download-delay']
        ))
        time.sleep(repo_conf['download-delay'])

    # now we are ready to fetch the build artifacts
    dl_path       = tempfile.mkdtemp()
    artifacts_zip = "{0}/artifacts.zip".format(dl_path)

    # download unpack and remove artifacts zip file
    git.select_project(data['project_id'])
    git.download_build_artifacts(data['build_id'], artifacts_zip)
    git.unzip(artifacts_zip, dl_path)
    os.remove(artifacts_zip)
    logger.info("{0} - Downloaded to: {1}".format(
        repo,
        dl_path
    ))

    # match packages with downloaded artifact files
    pkg_data = repo_conf['packages']
    pkgs_match = {}
    error_count = 0
    # loop over package dict in pkgbot-config
    for distro in pkg_data:
        pkgs_match[distro] = {}
        # loop over distro versions
        for version in pkg_data[distro]:
            pkgs_match[distro][version] = []
            glob_list = pkg_data[distro][version]
            if not isinstance(glob_list, (list, tuple)):
                glob_list = [pkg_data[distro][version]]
            # loop over glob list
            for item in glob_list:
                glob_str = "{0}/{1}".format(dl_path, item)
                glob_match = glob.glob(glob_str)
                # we consider it as an error, if more than one matches found
                # for a single glob
                if len(glob_match) > 1:
                    logger.error("{0} - Multiple matches on distro: {1} "
                                 "version: {2}  glob: '{3}'".format(
                                     repo,
                                     distro,
                                     version,
                                     item
                                 ))
                    error_count += 1
                elif len(glob_match) == 1:
                    pkgs_match[distro][version].append(glob_match[0])
            # if nothing found just delete the matches-element
            if not pkgs_match[distro][version]:
                logger.warning("{0} - No matches for distro: {1} version: "
                               "{2}".format(
                                   repo,
                                   distro,
                                   version,
                               ))
                del pkgs_match[distro][version]

    # if any errors found, cancel
    if error_count > 0:
        logger.error("{0} - Found {1} errors, will not continue".format(
            repo,
            error_count
        ))
        shutil.rmtree(dl_path)
        return

    # add packages to aptly/rpm
    aptly_add = []
    rpm_add = []
    has_aptly = False
    has_rpm   = False

    # loop over found files
    for distro in pkgs_match:
        # loop over distros
        for version in pkgs_match[distro]:
            # loop over distro versions
            for pkg in pkgs_match[distro][version]:

                # generate filenames
                package_dir = "{0}/{1}".format(
                    incoming_pkg_dir,
                    conf['pkgbot']['package-structure'][distro][version]
                )
                pkg_file     = os.path.basename(pkg)
                pkg_fullpath = "{0}/{1}".format(package_dir, pkg_file)
                aptly_repo   = "{0}-{1}-{2}".format(wanted_repo,
                                                    distro,
                                                    version
                                                    )

                # if the pkg-file allready exists, do nothing
                if os.path.isfile(pkg_fullpath):
                    logger.warning("{0} - File {1} allready exists, "
                                   "skipping".format(
                                       repo,
                                       pkg_file
                                   ))
                    continue

                logger.info("{0} - ADDPKG - distro: {1} version: {2} package: "
                            "{3}".format(
                                repo,
                                distro,
                                version,
                                pkg
                            ))

                # copy the file to incoming directory
                shutil.copyfile(pkg, pkg_fullpath)

                # store repo and file for aptly/createrepo
                if distro == 'rhel' or distro == 'centos':
                    has_rpm = True
                    rpm_add.append([pkg_fullpath,
                                    wanted_repo,
                                    distro,
                                    version
                                    ])
                else:
                    has_aptly = True
                    aptly_add.append([aptly_repo, pkg_fullpath])

    # everything copied, run aptly-commands
    aptly_pub = []
    for repo, pkg_path in aptly_add:
        os.write(fifo,"aptly repo add {0} {1}\n".format(
            repo,
            pkg_path
        ))
        aptly_pub.append(repo)

    if has_aptly:
        aptly_pub = list(set(aptly_pub))
        for repo in aptly_pub:
            endpoint       = "-".join(repo.split("-")[:-2])
            distro         = repo.split("-")[2]
            distro_version = repo.split("-")[3]
            pub_endpoint   = "{0}/{1}".format( endpoint, distro )
            os.write(fifo,"aptly publish update {0} {1}\n".format(
                distro_version,
                pub_endpoint
            ))

    #  if rpm files found, do nescesary stuff to add them
    if has_rpm:
        createrepo_distros = []
        for pkg_fullpath, repo, distro, version in rpm_add:
            # generate path
            pkg_basename = os.path.basename(pkg_fullpath)
            copy_to = "{0}/{1}/{2}/{3}".format(
                conf['pkgbot']['public-root'],
                repo,
                conf['pkgbot']['package-structure'][distro][version],
                pkg_basename
            )

            # copy file to final location
            try:
                shutil.copyfile(pkg_fullpath, copy_to)
            except IOError:
                logger.error("{0} - Error copying file: {1} to {2} ".format(
                    repo,
                    pkg_fullpath,
                    copy_to
                ))
                continue

            # sign rpm
            rpmsign_cmd = [
                conf['pkgbot']['scripts']['rpm-sign'],
                copy_to
            ]
            subprocess.check_call(rpmsign_cmd)
            createrepo_distros.append(
                conf['pkgbot']['package-structure'][distro][version]
            )

        # now all rpm packages are signed and at the correct location
        # run createrepo and sign repodata
        createrepo_distros = list(set(createrepo_distros))
        for distro in createrepo_distros:
            rpm_repo_path = "{0}/{1}/{2}".format(
                conf['pkgbot']['public-root'],
                wanted_repo,
                distro
            )
            # createrepo
            createrepo_cmd = [
                "createrepo",
                rpm_repo_path
            ]
            subprocess.check_call(createrepo_cmd)

            # sign repodata
            sign_repodata_cmd = [
                "gpg",
                "--yes",
                "--detach-sign",
                "--armor",
                "{0}/repodata/repomd.xml".format(
                    rpm_repo_path
                )
            ]
            subprocess.check_call(sign_repodata_cmd)

    # remove temporary dir
    shutil.rmtree(dl_path)
    # close fifo socket
    os.close(fifo)
    logger.info("{0} - Done adding packages".format(repo))
    return


class RequestHandler(BaseHTTPRequestHandler):
    """
    Class to handle incoming HTTP requests
    """
    def send_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write("")

    def do_GET(self):
        self.send_headers()
        return

    def do_POST(self):
        global conf
        data_string = self.rfile.read(int(self.headers['Content-Length']))
        data = json.loads(data_string)
        try:
            if (data['object_kind'] == "build" and
                    data['build_status'] == 'success'):
                threading.Thread(target=process_request, args=[data]).start()
        except:
            pass
        self.send_headers()

    def log_message(self, format, *args):
        logstr = (" ".join(map(str, args)))
        logger.info("REQUEST: {0}".format(logstr))


def main():
    global conf
    # load config
    try:
        with open(sys.argv[1]) as f:
            conf = yaml.load(f)
    except IOError as e:
        print(e)
        sys.exit(1)
    except (yaml.scanner.ScannerError, yaml.parser.ParserError, IndexError):
        print("ERROR: Cannot load config, YAML parser error")
        sys.exit(1)
    try:
        # start an http server
        server = HTTPServer(('', conf['pkgbot']['port']), RequestHandler)
        logger.info("Started {0} server on port {1}".format(
            __version__,
            conf['pkgbot']['port']
        ))
        server.serve_forever()
    except KeyboardInterrupt:
        server.socket.close()


if __name__ == "__main__":
    main()
