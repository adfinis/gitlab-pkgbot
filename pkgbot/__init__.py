#!/usr/bin/env python
# -*- coding: utf-8 -*-




import gitlab
import requests
import logging
import time
import threading
import yaml
import json
import pprint
import os
import sys
import zipfile
import tempfile
import shutil
from pprint import pprint
import glob
import urllib3

from distutils.dir_util import copy_tree
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from GitlabArtifacts import GitlabArtifactsDownloader


# init logging
def get_logger( prefix="adsy-pkgbot", project=False ):
    loggername = prefix
    if project:
        loggername = "{0} - {1}".format(prefix, project)
    logger = logging.getLogger(loggername)
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    proj_logger = get_logger(project=repo)
    proj_logger.info("Process build trigger")
    requests.packages.urllib3.disable_warnings()

    git = GitlabArtifactsDownloader(conf['gitlab']['url'], conf['gitlab']['token'])
    config_file = "/{0}/raw/{1}/.pkg-bot.yml".format( repo, data['ref'] )

    # TODO: better error checking
    try:
        repo_conf_dl = git.download_raw_file(config_file)
        rc = yaml.load(repo_conf_dl.text)
        repo_conf = rc['pkgbot']
        pkg_data = repo_conf['packages']
        valid_branches = repo_conf['branches']
    except:
        proj_logger.error("config for repo not found or invalid")
        return

    # branch is required in config
    if data['ref'] not in valid_branches:
        proj_logger.info("branch: {0} does not match any configured".format(
            data['ref']
        ))
        return

    # stages are optional
    if 'stages' in repo_conf:
        if data['build_stage'] not in repo_conf['stages']:
            proj_logger.info("Build stage {0} does not match any configured".format(
                data['build_stage']
            ))
            return

    # gitlab ci will trigger an build done event and then start to upload the artifacts.
    # users can configure an delay before downloading artifacts
    if 'download-delay' in repo_conf:
        proj_logger.info("Config has delay in it, sleep for {0} secs".format(repo_conf['download-delay']))
        time.sleep(repo_conf['download-delay'])

    # now we are ready to fetch the build artifacts
    dl_path = tempfile.mkdtemp()
    artifacts_zip = "{0}/artifacts.zip".format( dl_path )
    git.select_project(data['project_id'])
    git.download_last_artifacts( artifacts_zip )
    git.unzip( artifacts_zip, dl_path )
    # remove artifacts zip
    os.remove(artifacts_zip)
    proj_logger.info("downloaded to: {0}".format(dl_path))

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
                glob_list = [ pkg_data[distro][version] ]
            # loop over glob list
            for item in glob_list:
                glob_str = "{0}/{1}".format(dl_path, item)
                glob_match = glob.glob(glob_str)
                # we consider it as an error, if more than one matches found for
                # a single glob
                if len(glob_match)>1:
                    proj_logger.error("Multiple matches on distro: {0} version: {1}  glob: '{2}'".format(
                        distro,
                        version,
                        item
                    ))
                    error_count+=1
                elif len(glob_match) == 1:
                    pkgs_match[distro][version].append(glob_match[0])
            # if nothing found just delete the matches-element
            if not pkgs_match[distro][version]:
                proj_logger.warning("No matches for distro: {0} version: {1}".format(
                    distro,
                    version,
                ))
                del pkgs_match[distro][version]

    # if any errors found, cancel
    if error_count>0:
        proj_logger.error("Found {0} errors, will not continue".format( error_count ))
        shutil.rmtree(dl_path)
        return

    # add packages to aptly/rpm
    for distro in pkgs_match:
        for version in pkgs_match[distro]:
            for pkg in pkgs_match[distro][version]:
                proj_logger.info("ADDPKG - distro: {0} version: {1} package: {2}".format(
                    distro,
                    version,
                    pkg
                ))


    # remove temporary dir
    shutil.rmtree(dl_path)
    proj_logger.info("done adding packages")
    return


class RequestHandler(BaseHTTPRequestHandler):
    """
    Class to handle incoming HTTP requests
    """
    def send_headers(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
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
             if (data['object_kind'] == "build" and data['build_status']=='success'):
                 thread = threading.Thread( target=process_request, args=[data] )
                 thread.start()
        except:
            pass
        self.send_headers()

    def log_message(self, format, *args):
        logstr = (" ".join(map(str, args)) )
        logger.info("REQUEST: {0}".format(logstr))


def main():
    global conf
    # load config
    with open(sys.argv[1]) as f:
        conf = yaml.load(f)
    try:
        # start an http server
        server = HTTPServer(('', conf['pkgbot']['port']), RequestHandler )
        logger.info("Started server on port {0}".format(conf['pkgbot']['port']))
        server.serve_forever()
    except KeyboardInterrupt:
        server.socket.close()

if __name__ == "__main__":
    main()
