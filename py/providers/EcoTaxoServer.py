# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A client to EcoTaxoServer (the central taxonomy point for all EcoTaxa instances).
# @see https://github.com/ecotaxa/ecotaxoserver
#
from typing import Dict, Any

import requests


class EcoTaxoServerClient(object):
    """
    A class encapsulating the dialog with EcoTaxoServer.
    """

    def __init__(self, url: str, instance_id: str, secret_key: str):
        """
        :param instance_id: EcoTaxa instance identifier.
        :param secret_key: A secret key, associated with the identifier, granted by EcoTaxoServer.
        """
        self.url = url
        self.instance_id = instance_id
        self.secret_key = secret_key

    def call(self, endpoint: str, endpoint_params: Dict[str, Any]):
        """
        Issue a REST query on EcoTaxoServer
        """
        params = {
            "id_instance": self.instance_id,
            "sharedsecret": self.secret_key,
            "ecotaxa_version": "2.5.11",  # TODO: Wondering why this param
        }
        params.update(endpoint_params)
        r = requests.post(
            self.url + endpoint, params
        )  # TODO: Use some async lib instead of requests
        return r.json()
