# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Basic test of client API
#
import time
from typing import Optional

import requests

from eco_taxa_client.client import AuthenticatedClient
import eco_taxa_client.api.projects as project_api
import eco_taxa_client.api.users as users_api

# Needed due to usage of this primitive in generated code
from backports.datetime_fromisoformat import MonkeyPatch

from eco_taxa_client.models import CreateProjectReq

# Inject the fromisoformat def into time classes
MonkeyPatch.patch_fromisoformat()

BASE_URL = "http://localhost:5000"


# prod
# BASE_URL="https://ecotaxa.obs-vlfr.fr"


class EcoTaxaApiClient(object):
    """
        An API client wrapper class for Ecotaxa.
    """

    def __init__(self, url: str, login: str, password: str):
        self.url = url
        self.login = login
        self.password = password
        self.session = requests.session()
        self.client: Optional[AuthenticatedClient] = None

    def open(self):
        """
            Open a connection to the API by logging in.
        """
        csrf_tok = self._get_csrf()
        session_tok = self._log_in(csrf_tok)
        self.token = session_tok
        assert self.token is not None, "Auth failed!"
        self.client = AuthenticatedClient(self.api_url, self.token)

    @property
    def login_url(self):
        return self.url + "/login"

    @property
    def api_url(self):
        return self.url + "/api"

    @staticmethod
    def _extract_csrf_token(page) -> str:
        """
            Extract crsf token from login page HTML.
        """
        for a_line in page.splitlines():
            if 'id="csrf_token"' in a_line:
                # <input id="csrf_token" name="csrf_token" type="hidden" value="ImQ5YjY5Mzc0MDZmMj...">
                return a_line.split('"')[7]

    def _get_csrf(self):
        """
            GET the login page, for extracting the CSRF token.
        """
        rsp = self.session.get(self.login_url)
        return self._extract_csrf_token(rsp.text)

    LOGOUT_HTML = '<a href="/logout">log out</a>'

    def _log_in(self, tok: str):
        """
            POST the login form, just like the HTML does.
        """
        pseudo_form = {"email": self.login,
                       "password": self.password,
                       "csrf_token": tok}
        rsp = self.session.post(url=self.login_url, data=pseudo_form)
        if self.LOGOUT_HTML in rsp.text:
            # We can logout only when we're in :)
            return self.session.cookies["session"]
        else:
            return None

    def whoami(self):
        """
            Example API call for fetching own name.
        """
        rsp = users_api.current_user_users_me_get(client=self.client)
        print(rsp.name)

    def can_i_view(self):
        """
            Example API call for fetching allowed projects
        """
        rsp = project_api.search_projects_projects_search_get(client=self.client, title_filter="New")
        print(len(rsp), "Projects")

    def add_a_project(self, title):
        """
            Example API call for simple project creation
        """
        req = CreateProjectReq(title=title)
        rsp = project_api.create_project_projects_create_post(client=self.client, json_body=req)
        print(rsp)


def main():
    # /!\ Don't hardcode credentials in source code, especially if it goes to GH /!\
    client = EcoTaxaApiClient(url=BASE_URL,
                              login="laurent.salinas@laposte.net",
                              password="PouEcoT98;")
    client.open()
    start = time.time()
    client.whoami()
    client.can_i_view()
    client.add_a_project("New proj")
    #
    client_prj_creator = EcoTaxaApiClient(url=BASE_URL,
                                          login="laurent.salinas@obs-vlfr.fr",
                                          password="toto12")
    client_prj_creator.open()
    client_prj_creator.add_a_project("OK for prj creator")
    #
    client_no_rights = EcoTaxaApiClient(url=BASE_URL,
                                        login="laurent.salinas@gmail.com",
                                        password="toto12")
    client_no_rights.open()
    client_no_rights.add_a_project("KO for quidam")
    # client.can_i_view(session_tok)
    print("Duration: %0.fms" % ((time.time() - start) * 1000))


if __name__ == '__main__':
    main()
