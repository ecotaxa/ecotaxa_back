from starlette import status

SEARCH_WORMS_URL = "/searchworms/{}"

ACARTIA_RSP = [
    {
        "aphia_id": 104108,
        "name": "Acartia",
        "rank": "Genus",
        "status": "accepted",
        "lineage": {
            "104108": {
                "AphiaID": 104074,
                "rank": "Family",
                "scientificname": "Acartiidae",
            },
            "104074": {"AphiaID": 1100, "rank": "Order", "scientificname": "Calanoida"},
            "1100": {
                "AphiaID": 155877,
                "rank": "Superorder",
                "scientificname": "Gymnoplea",
            },
            "155877": {
                "AphiaID": 155876,
                "rank": "Infraclass",
                "scientificname": "Neocopepoda",
            },
            "155876": {"AphiaID": 1080, "rank": "Class", "scientificname": "Copepoda"},
            "1080": {
                "AphiaID": 845959,
                "rank": "Superclass",
                "scientificname": "Multicrustacea",
            },
            "845959": {
                "AphiaID": 1066,
                "rank": "Subphylum",
                "scientificname": "Crustacea",
            },
            "1066": {"AphiaID": 1065, "rank": "Phylum", "scientificname": "Arthropoda"},
            "1065": {"AphiaID": 2, "rank": "Kingdom", "scientificname": "Animalia"},
            "2": {"AphiaID": 1, "rank": "Superdomain", "scientificname": "Biota"},
        },
        "id": 80116,
    }
]


def test_search_worms_name(fastapi, mocker):
    # Mock the 'call' method of EcoTaxoServerClient
    mock_call = mocker.patch("providers.EcoTaxoServer.EcoTaxoServerClient.call")
    mock_response = mocker.Mock()
    mock_response.json.return_value = ACARTIA_RSP
    mock_call.return_value = mock_response

    url = SEARCH_WORMS_URL.format("Acartia")
    # Unauthenticated call
    rsp = fastapi.get(url)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == ACARTIA_RSP

    # Verify the mock was called correctly
    mock_call.assert_called_with("/wormstaxon/Acartia", {}, "get")
