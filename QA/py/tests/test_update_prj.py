import logging
from copy import deepcopy
from urllib.parse import urlencode, quote

from starlette import status

from tests.credentials import ADMIN_AUTH, ORDINARY_USER_USER_ID, ORDINARY_USER2_USER_ID, USER2_AUTH, USER_AUTH
from tests.test_fastapi import PROJECT_QUERY_URL

PROJECT_UPDATE_URL = "/projects/{project_id}"

PROJECT_SETTINGS_UPDATE_URL = "/projects/{project_id}/prediction_settings?settings={settings}"


def test_update_prj(config, database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import_uvp6
    prj_id = test_import_uvp6(config, database, caplog, "Test Project Updates")
    # Do like in legacy app, i.e. fetch/modify/resend
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    ref_json = {'acquisition_free_cols': {'aa': 't03',
                                          'exp': 't04',
                                          'gain': 't06',
                                          'pixel': 't05',
                                          'ratio': 't10',
                                          'smbase': 't08',
                                          'smzoo': 't09',
                                          'sn': 't01',
                                          'threshold': 't07',
                                          'volimage': 't02'},
                'annotators': [],
                'bodc_variables': {},
                'highest_right': 'Manage',
                'classiffieldlist': None,
                'classifsettings': None,
                'cnn_network_id': None,
                'comments': None,
                'contact': None,
                'instrument': 'UVP6',
                'instrument_url': 'http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/',
                'init_classif_list': [],
                'license': '',
                'managers': [{'email': 'administrator',
                              'id': 1,
                              'name': 'Application Administrator'}],
                'obj_free_cols': {'%area': 'n23',
                                  'angle': 'n16',
                                  'area': 'n01',
                                  'area_exc': 'n24',
                                  'circ.': 'n17',
                                  'circex': 'n51',
                                  'convarea': 'n39',
                                  'convarea_area': 'n55',
                                  'convperim': 'n38',
                                  'convperim_perim': 'n54',
                                  'cv': 'n45',
                                  'elongation': 'n42',
                                  'fcons': 'n40',
                                  'feret': 'n18',
                                  'feretareaexc': 'n48',
                                  'fractal': 'n25',
                                  'height': 'n13',
                                  'histcum1': 'n28',
                                  'histcum2': 'n29',
                                  'histcum3': 'n30',
                                  'intden': 'n19',
                                  'kurt': 'n22',
                                  'kurt_mean': 'n52',
                                  'major': 'n14',
                                  'max': 'n06',
                                  'mean': 'n02',
                                  'meanpos': 'n44',
                                  'median': 'n20',
                                  'median_mean': 'n64',
                                  'median_mean_range': 'n65',
                                  'min': 'n05',
                                  'minor': 'n15',
                                  'mode': 'n04',
                                  'nb1': 'n31',
                                  'nb1_area': 'n58',
                                  'nb1_range': 'n61',
                                  'nb2': 'n32',
                                  'nb2_area': 'n59',
                                  'nb2_range': 'n62',
                                  'nb3': 'n33',
                                  'nb3_area': 'n60',
                                  'nb3_range': 'n63',
                                  'perim.': 'n11',
                                  'perimareaexc': 'n47',
                                  'perimferet': 'n49',
                                  'perimmajor': 'n50',
                                  'range': 'n43',
                                  'skelarea': 'n26',
                                  'skeleton_area': 'n66',
                                  'skew': 'n21',
                                  'skew_mean': 'n53',
                                  'slope': 'n27',
                                  'sr': 'n46',
                                  'stddev': 'n03',
                                  'symetrieh': 'n34',
                                  'symetrieh_area': 'n56',
                                  'symetriehc': 'n36',
                                  'symetriev': 'n35',
                                  'symetriev_area': 'n57',
                                  'symetrievc': 'n37',
                                  'thickr': 'n41',
                                  'width': 'n12',
                                  'x': 'n07',
                                  'xm': 'n09',
                                  'y': 'n08',
                                  'ym': 'n10'},
                'objcount': 15.0,
                'pctclassified': None,
                'pctvalidated': 0.0,
                'popoverfieldlist': None,
                'process_free_cols': {'date': 't02',
                                      'first_img': 't04',
                                      'fontcolor': 't10',
                                      'fontheight_px': 't11',
                                      'footerheight_px': 't12',
                                      'gamma': 't06',
                                      'invert': 't07',
                                      'keeporiginal': 't09',
                                      'last_img': 't05',
                                      'scale': 't13',
                                      'scalebarsize_mm': 't08',
                                      'software': 't01',
                                      'time': 't03'},
                'projid': prj_id,
                'description': None,
                'rf_models_used': None,
                'sample_free_cols': {'argoid': 't17',
                                     'barcode': 't14',
                                     'bottomdepth': 't05',
                                     'comment': 't13',
                                     'cruise': 't02',
                                     'ctdrosettefilename': 't06',
                                     'dn': 't07',
                                     'integrationtime': 't16',
                                     'nebuloussness': 't11',
                                     'profileid': 't01',
                                     'sampledatetime': 't18',
                                     'sampletype': 't15',
                                     'seastate': 't10',
                                     'ship': 't03',
                                     'stationid': 't04',
                                     'winddir': 't08',
                                     'windspeed': 't09',
                                     'yoyo': 't12'},
                'status': 'Annotate',
                'title': 'Test Project Updates',
                'viewers': [],
                'visible': True}

    read_json = rsp.json()
    assert read_json == ref_json

    upd_json = deepcopy(read_json)
    contact_usr = upd_json["managers"][0]
    # Attempt to reproduce ecotaxa/ecotaxa_dev#596
    # del contact_usr['usercreationdate']
    # contact_usr['usercreationdate'] = None
    # del contact_usr['usercreationreason']

    url = PROJECT_UPDATE_URL.format(project_id=prj_id)
    upd_json["comments"] = "New comment"
    upd_json["contact"] = contact_usr
    upd_json["visible"] = False
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=upd_json)
    assert rsp.status_code == status.HTTP_200_OK

    # Re-read
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=False)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.json() != ref_json
    assert rsp.json()["comments"] == "New comment"
    assert rsp.json()["visible"] is False

    # For ecotaxa/ecotaxa_dev#602
    # Set no contact at all
    no_contact_upd = deepcopy(read_json)
    no_contact_upd["contact"] = None
    url = PROJECT_UPDATE_URL.format(project_id=prj_id)
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=no_contact_upd)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert rsp.text == '{"detail":"A valid Contact is needed."}'

    # Set a contact with wrong id
    wrong_contact_upd = deepcopy(read_json)
    wrong_contact_upd["contact"] = {"id": ORDINARY_USER2_USER_ID,
                                    "name": "name",
                                    "email": "toto@titi.com"}
    url = PROJECT_UPDATE_URL.format(project_id=prj_id)
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=wrong_contact_upd)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert rsp.text == '{"detail":"Could not set Contact, the designated user is not in Managers list."}'


def test_update_prj_pred_settings(config, database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import_uvp6
    prj_id = test_import_uvp6(config, database, caplog, "Test Project Settings Updates")
    # Do like in legacy app, i.e. fetch/modify/resend
    qry_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(qry_url, headers=ADMIN_AUTH)
    read_json = rsp.json()
    assert read_json['classifsettings'] is None

    # Not possible if not a project member
    new_settings = "My new project settings"
    sett_url = PROJECT_SETTINGS_UPDATE_URL.format(project_id=prj_id, settings=quote(new_settings))
    rsp = fastapi.put(sett_url, headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Grant an ordinary user the annotator right
    usr = {"id": ORDINARY_USER_USER_ID, "email": "ignored", "name": "see email"}
    mgr = {"id": ORDINARY_USER2_USER_ID, "email": "ignored", "name": "see email"}
    read_json['annotators'].append(usr)
    read_json['managers'].append(mgr)
    read_json['contact'] = mgr  # Setting a manager and a contact is mandatory
    upd_url = PROJECT_UPDATE_URL.format(project_id=prj_id)
    rsp = fastapi.put(upd_url, headers=ADMIN_AUTH, json=read_json)
    assert rsp.status_code == status.HTTP_200_OK

    # Now it should be OK
    rsp = fastapi.put(sett_url, headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_200_OK

    # Check
    rsp = fastapi.get(qry_url, headers=ADMIN_AUTH)
    read_json = rsp.json()
    assert read_json['classifsettings'] == new_settings
