#
# UI smoke tests for ecotaxa
#
# Based on selenium tool
#

import pytest

pytest.register_assert_rewrite("testingUtils")

from pageTest import PageToTest
# processes and driver might seem unused but they are pytest fixtures so removing will break tests
# noinspection PyUnresolvedReferences
from testingUtils import do_one_page, processes, driver, do_input, do_check




def test_processes_up(processes):
    """
        Start with a simple test which ensures environment is OK.
        Thus timings of following tests is not impacted by bringing the environment up.
    """
    assert processes.is_up_and_running()


"""
/part
/prj/1  # login
/search/taxo
/search/taxotreejson
/search/taxotree?target="+targetid
/search/taxoresolve
/search/mappopup/?a=b
/search/mappopup/getsamplepopover/'+feature.get('sampleid')
"""

public_pages = [
    PageToTest("/", "root"),
    # Redirects to /login?next=%2Fprj%2F as there is no login
    PageToTest("/prj/", "prjSelect"),
    PageToTest("/login", "login"),
    PageToTest("/register", "register"),
    # Note: The rendering of these (complex) pages depends on navigator window size
    PageToTest("/explore/", "explore"),
    PageToTest("/explore/?projid=1", "explorePrj1"),
    # A control there shows current _time_, thus the reference becomes invalid after a while
    PageToTest("/prj/1", "prj1ReadOnly").has_random("xdsoft_current").has_random("xdsoft_today"),
    PageToTest("/prj/99999999", "nonExistingProject"),
    PageToTest("/ajaxcoutrylist", "countrylist"),
    PageToTest("/search/users?q=%%#", "userlist"),
    PageToTest("/search/instrumlist", "instrumentList"),
    PageToTest("/search/exploreproject", "exploreProject").is_json(),
    PageToTest("/search/annot/1", "annotProject1"),
    PageToTest("/search/samples?format=J&q=&projid=1", "samplesProject1").is_json(),
    PageToTest("/privacy", "privacy")
]


@pytest.mark.parametrize("a_page", public_pages)
def test_public(processes, driver, a_page: PageToTest):
    """
        Test a public page, i.e. what one can see without login.
    """
    assert processes.is_up_and_running()
    # All is done in testingUtils
    do_one_page(driver, base_url + a_page.url, a_page.expected, a_page.randoms)


admin_login = {"email": "admin", "password": "ecotaxa"}
# For an unknown reason the login must be done twice
admin_login_twice = [admin_login, admin_login]
login_ok = {"divheadinfo": """Application Administrator (log out)
Action
Toggle Dropdown"""}
admin_pages = [
    # Refactoring issue here: the login page is generated in flask, no template
    PageToTest("/login", "login").then_input(admin_login_twice).then_check(login_ok),
    PageToTest("/prj/?filt_title=LS&filt_instrum=zooscan", "prjAsAdmin"),
    PageToTest("/prjothers/", "prjOthersAsAdmin"),
    PageToTest("/prj/edit/1", "prjEditAsAdmin"),  # TODO: Get/post here
    PageToTest("/prj/editpriv/1", "prjEditPrivAsAdmin"),  # TODO: Get/post here
    PageToTest("/prj/editdatamass/1", "prjEditDataMassAsAdmin"),  # TODO: Get/post here
    PageToTest("/prj/resettopredicted/1", "prjResetToPredictedAsAdmin"),  # TODO: Get/post here

    PageToTest("/Task/listall", "taskListAll"),  # TODO: Get/post here

    PageToTest("/admin/", "adminAsAdmin"),
    # TODO: Several csrf token there
    # PageToTest("/admin/users/", "adminUsers"),
    PageToTest("/admin/projectlight/", "adminProjectLight"),
    # TODO: Several csrf token there
    # PageToTest("/admin/projects/", "adminProjects"),
    PageToTest("/admin/objects/", "adminObjects"),
    PageToTest("/admin/objectsfields/", "adminObjectFields"),
    PageToTest("/admin/samples/", "adminSamples"),
    PageToTest("/admin/process/", "adminProcess"),
    PageToTest("/admin/acquisitions/", "adminAcquisition"),
    PageToTest("/admin/taxonomy/", "adminTaxonomy"),

    # Below has random order in a HTML table
    # see in appli/search/dbadmin.py
    PageToTest("/dbadmin/viewsizes", "dbViewSizes"),
    # Below has random order in a HTML table
    # see dbadmin_viewtaxoerror in appli/search/dbadmin.py
    PageToTest("/dbadmin/viewtaxoerror", "viewTaxoError"),
    # Below has random order in a HTML table
    # see in appli/search/dbadmin.py
    PageToTest("/dbadmin/viewbloat", "viewBloat"),
    PageToTest("/dbadmin/recomputestat", "recomputeStat"),

    PageToTest("/dbadmin/merge2taxon", "merge2taxon"),  # TODO: Get here

    PageToTest("/dbadmin/console", "dbConsole"),  # TODO: Get/post here

    PageToTest("/logout", "logoutAsAdmin")
]


@pytest.mark.parametrize("a_page", admin_pages)
def test_admin(processes, driver, a_page: PageToTest):
    """
        Test an administrator page, needing an administrator session.
    """
    assert processes.is_up_and_running()
    # All is done in testingUtils
    do_one_page(driver, base_url + a_page.url, a_page.expected, a_page.randoms)
    # If we get here then the test passed, proceed to dialog
    do_input(driver, a_page.input)
    do_check(driver, a_page.after_input_check)
