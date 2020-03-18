#
# Perf test around import
#

import time
import re

# noinspection PyUnresolvedReferences
import pytest

from selenium.webdriver.remote.webdriver import WebDriver

from appli.tests.processes import TstProcesses
from appli.tests.uiUtils import MyDriver
from appli.tests.testingUtils import do_one_page, base_url
# Fixtures
# noinspection PyUnresolvedReferences
from appli.tests.testingUtils import driver, processes

admin_login = {"email": "admin", "password": "ecotaxa"}
# For an unknown reason the login must be done twice
admin_login_twice = [admin_login, admin_login]
login_ok = {"divheadinfo": re.compile("""^.*(
)?Application Administrator [(]log out[)]
Action
Toggle Dropdown$""", re.MULTILINE)}


def test_import(processes: TstProcesses, driver: WebDriver):
    # Check all OK on srv side
    assert processes.is_up_and_running()
    # Smoke test Web server, it's a static page
    do_one_page(driver, base_url, "home", [])
    drv = MyDriver(driver, base_url)
    login(drv)
    create_project(drv)
    taxoserver_sync(drv)
    import_file(drv)
    do_db_dump("taxonomy.dmp")
    #
    # pg_dump -h localhost -U postgres -d ecotaxa -t taxonomy -f taxonomy.dmp
    #
    time.sleep(20)

def do_db_dump(file_name):
    pass

def login(drv: MyDriver):
    drv.get("/login")
    drv.do_input(admin_login)
    drv.do_check(login_ok)


def create_project(drv: MyDriver):
    # Create a minimal project
    drv.get("/prj/")
    btn = drv.find_element_by_id("CreatePrjBtn")
    btn.click()
    # JS: A hidden DIV should appear
    btn = drv.find_element_by_id("newprojecttitle")
    btn.send_keys("TestLS")
    btn = drv.find_element_by_id("DoCreateProject")
    btn.click()
    # POST: There is a redirect to the newly created project
    drv.wait_for_div_appears(id_="topbar")


def taxoserver_sync(drv: MyDriver):
    # Synchronize with EcotaxoServer
    drv.get("/taxo/browse/")
    sync_btn = drv.find_element_by_id("DoSyncBtn")
    sync_btn.click()
    # Wait until the sync popup appears
    drv.wait_for_div_appears(clazz="At2PopupWindow")
    # Wait until the sync popup disappears
    drv.wait_for_div_disappears(clazz="At2PopupWindow")


def import_file(drv: MyDriver):
    # Go to Import page
    drv.get("/Task/Create/TaskImport?p=1")
    # Fill fields
    file_btn = drv.find_element_by_id("ServerPath")
    file_btn.send_keys("task_24389_export_372_20190801_1246.zip")
    start_btn = drv.find_element_by_id("StartImportBtn")
    start_btn.click()
    # Wait for the question and Go button to appear
    drv.wait_for_div_contains("Question waiting your Answer", id_="statusDiv")
    go_btn = drv.find_element_by_id("GoBtn")
    go_btn.click()
    # Name & taxo resolution page should appear
    drv.wait_for_div_appears(clazz="divheadinfo")
    # Answer the name resolution
    user_select = drv.find_element_by_class("select2-selection")
    user_select.click()
    time.sleep(0.1)
    user_lookup = drv.find_element_by_class("select2-search__field")
    user_lookup.send_keys("admin"+u'\ue007')
    # TODO: Wait for "Administrator" to appear in the DOM
    time.sleep(0.5)
    user_lookup.send_keys(u'\ue007')
    # Continue to import
    continue_btn = drv.find_element_by_id("ContinueBtn")
    continue_btn.click()
    # Wait for completion
    drv.wait_for_div_contains("Task Complete :Processing done", id_="statusDiv")


def no_test_import(processes: TstProcesses, driver: WebDriver):
    assert processes.is_up_and_running(do_create_db=False, do_launch_server=True)
    drv = MyDriver(driver, base_url)
    login(drv)
    import_file(drv)
