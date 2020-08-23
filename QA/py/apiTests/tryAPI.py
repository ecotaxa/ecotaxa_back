# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Basic test of client API
#
import time

import requests

from ecotaxa_cli_py import DefaultApi, Configuration, ApiClient, ApiException, User

BASE_URL = "http://localhost:5000"
# prod
# BASE_URL="https://ecotaxa.obs-vlfr.fr"
API_URL = BASE_URL + "/api"


class EcoTaxaApiClient(object):
    """
        An API client wrapper class for Ecotaxa.
    """

    def __init__(self, url: str, login: str, password: str):
        self.url = url
        self.login = login
        self.password = password
        self.session = requests.session()
        self.token: str = ""

    def open(self):
        """
            Open a connection to the API by logging in.
        """
        csrf_tok = self._get_csrf()
        session_tok = self._log_in(csrf_tok)
        self.token = session_tok
        assert self.token is not None, "Auth failed!"
        configuration = Configuration(
            host=self.api_url
        )
        configuration.access_token = self.token

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
            Fetch the login page a first time, for extracting the CSRF token.
        """
        rsp = self.session.get(self.login_url)
        return self._extract_csrf_token(rsp.text)

    LOGOUT_HTML = '<a href="/logout">log out</a>'

    def _log_in(self, tok: str):
        """
            Post the login form, just like the HTML does.
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
        configuration = Configuration(
            host=self.api_url
        )
        configuration.access_token = self.token

        # Enter a context with an instance of the API client
        with ApiClient(configuration) as api_client:
            # Create an instance of the API class
            api_instance = DefaultApi(api_client)
            try:
                # Current User
                api_response: User = api_instance.current_user_users_me_get()
                print(api_response.name)
            except ApiException as e:
                print("Exception when calling DefaultApi->current_user_users_me_get: %s\n" % e)

    def can_i_view(self):
        """
            Example API call for fetching allowed projects
        """


        # Enter a context with an instance of the API client
        with ApiClient(configuration) as api_client:
            # Create an instance of the API class
            api_instance = DefaultApi(api_client)
            try:
                # Current User
                api_response: User = api_instance.search_projects_projects_search_get()
                print(len(api_response))
            except ApiException as e:
                print("Exception when calling DefaultApi->get_projects_projects_get: %s\n" % e)


def main():
    # /!\ Don't hardcode credentials in source code, especially if it goes to GH /!\
    client = EcoTaxaApiClient(url=BASE_URL,
                              login="laurent.salinas@laposte.net",
                              password="PouEcoT98;")
    client.open()
    start = time.time()
    client.whoami()
    # client.can_i_view(session_tok)
    print("Dur: %ds", time.time() - start)


if __name__ == '__main__':
    main()
