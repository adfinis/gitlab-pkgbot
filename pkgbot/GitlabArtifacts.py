#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys
import gitlab
import zipfile
import requests
from distutils.dir_util import copy_tree


class GitlabArtifactsDownloader:
    """
    Class to download and exract build aritfacts from gitlab
    """
    def __init__(self, gitlab_url, gitlab_token):
        # disable annoying sslcontext warnings
        requests.packages.urllib3.disable_warnings()
        self.gitlab_url = gitlab_url
        self.project = False
        self.git = gitlab.Gitlab(
            gitlab_url,
            gitlab_token,
            ssl_verify=False
        )


    def select_project_search(self, project_name):
        project = self.git.projects.search(project_name)
        if len(project)<1:
            self.project = False
            return False
        else:
            self.project = project[0]
            return True


    def select_project(self, project_id):
        self.project = self.git.projects.get(project_id)


    def download_last_artifacts(self, local_filename):
        if self.project:
            # fetch last build from api
            builds = self.project.builds.list()
            last_build = builds[0]
            artifacts_dl_url = "{0}/builds/{1}/artifacts/download".format(
                self.project.path_with_namespace,
                last_build.id
            )
            # save git api url
            git_urlsave = self.git._url
            # set gitlab url to main for downloading artifact
            self.git._url = "{0}/".format(self.gitlab_url)
            # download artifact
            dl = self.git._raw_get(artifacts_dl_url)
            # restore original api error
            self.git._url = git_urlsave
            self.save_download(dl, local_filename)


    def save_download(self, dl, local_filename):
        f = open(local_filename, 'wb')
        # loop over all chunks and append them to file
        for chunk in dl.iter_content(chunk_size=512 * 1024):
            # filter out keepalive packages
            if chunk:
                f.write(chunk)
        f.close()
        return


    def unzip(self, filename, extract_to):
        try:
            with zipfile.ZipFile(filename, "r") as z:
                z.extractall(extract_to)
        except:
            pass


    def download_raw_file(self, path):
        git_urlsave = self.git._url
        # set gitlab url to main for downloading artifact
        self.git._url = "{0}/".format(self.gitlab_url)
        dl = self.git._raw_get(path)
        # restore original api error
        self.git._url = git_urlsave
        return dl
