# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
from providers.EcoTaxoServer import EcoTaxoServerClient


def test_ecotaxoserver_call_passes_timeout(mocker):
    client = EcoTaxoServerClient(
        url="https://ecotaxoserver.example.org",
        instance_id="42",
        secret_key="secret",
    )

    mock_get = mocker.patch("requests.get")
    mock_post = mocker.patch("requests.post")

    client.call("/wormstaxon/Acartia", {"extra": "1"}, method="get")
    mock_get.assert_called_once_with(
        "https://ecotaxoserver.example.org/wormstaxon/Acartia",
        {
            "id_instance": 42,
            "sharedsecret": "secret",
            "ecotaxa_version": "2.5.11",
            "extra": "1",
        },
        timeout=EcoTaxoServerClient.TIMEOUT,
    )

    client.call("/gettaxon/", {"filtertype": "id", "id": 1})
    mock_post.assert_called_once_with(
        "https://ecotaxoserver.example.org/gettaxon/",
        {
            "id_instance": 42,
            "sharedsecret": "secret",
            "ecotaxa_version": "2.5.11",
            "filtertype": "id",
            "id": 1,
        },
        timeout=EcoTaxoServerClient.TIMEOUT,
    )
