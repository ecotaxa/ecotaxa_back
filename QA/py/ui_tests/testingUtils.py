#
#  UI (Web) testing base layer for ecotaxa.
#
# You need:
#       A chromedriver binary from https://sites.google.com/a/chromium.org/chromedriver/downloads
#

import os.path as os_path
import time
from os import unlink
from pathlib import Path

import pytest
# Driver binary, assumed to be present in current path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from appli.tests.processes import TstProcesses

# Base ecotaxa url, the one from "python runserver.py"
# TODO: Get it from runserver.py output
base_url = "http://0.0.0.0:5000"

# To customize
driver_exe_path = os_path.join("/home/laurent/Devs", "chromedriver")
# Where expected are found
expected_dir = Path("expected")
# Whare actual is dumped
actual_dir = Path("actual")


# Fixture for ensuring we have the servers
@pytest.fixture(scope="module")
def processes() -> TstProcesses:
    # Setup
    flask_and_pg = TstProcesses()
    yield flask_and_pg
    # Teardown
    flask_and_pg.shutdown()
    TstProcesses.generate_coverage()


# Fixture for Chrome
@pytest.fixture(scope="module")
def driver() -> WebDriver:
    options = Options()
    options.binary_location = "/usr/bin/chromium-browser"
    chrome_driver = webdriver.Chrome(driver_exe_path, options=options)
    # Fix the size for pages based on browser window
    chrome_driver.set_window_size(1200, 1024)
    yield chrome_driver
    chrome_driver.close()
    chrome_driver.quit()
    # Workaround as in https://github.com/SeleniumHQ/selenium/pull/6941/commits/367fb815453cb021c3045575079a0560ff91a7a5
    if hasattr(chrome_driver.command_executor, '_conn'):
        # noinspection PyProtectedMember
        chrome_driver.command_executor._conn.clear()


def do_one_page(driver: WebDriver, url, expected_file_name, random_strings):
    # Open the given URL
    driver.get(url)
    # Get what the navigator displays
    page = _get_page(driver)
    # Remove random values
    for a_random in random_strings:
        if a_random in page:
            page = page.replace(a_random, "")
    # Save actual
    actual_dump_path = os_path.join(actual_dir, expected_file_name + ".html")
    with open(actual_dump_path, "w") as act_out:
        act_out.write(page)
    # Compare with expected
    expected_path = os_path.join(expected_dir, expected_file_name + ".html")
    with open(expected_path) as exp_out:
        expected_page = exp_out.read()
    assert expected_page == page
    # If test is OK, remove the actual which is useless
    unlink(actual_dump_path)


def _do_input(driver: WebDriver, dialog: dict):
    """
        Fill-in a form and submit it.
    """
    # Simply send keys to the HTML element
    # This way no need to worry about input type (text, checkbox, select, ...)
    last_elem = None
    for elem_id, value in dialog.items():
        elem: WebElement = driver.find_element_by_id(elem_id)
        elem.send_keys(value)
        last_elem = elem
    # Find the enclosing form and submit it
    last_elem.submit()


def do_input(driver: WebDriver, dialog):
    """
        Fill-in a form and submit it, repeated if dialog is a list.
    """
    if dialog is None:
        return
    if isinstance(dialog, list):
        for a_dialog in dialog:
            _do_input(driver, a_dialog)
    else:
        _do_input(driver, dialog)


def do_check(driver: WebDriver, check: dict):
    if check is None:
        return
    # Verify visual value of given element in page
    for elem_id, value in check.items():
        elem: WebElement = driver.find_element_by_id(elem_id)
        elem_val = elem.text
        assert elem_val == value


def _get_page(driver: WebDriver):
    # Comparison will always fail if we don't map random data to constants
    _remove_unpredictable_from_DOM(driver)

    ret: str = driver.page_source

    # In html, but _only_ during async loading of image:
    # <img ... src="data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
    # Then the navigator loads the jpg and it becomes:
    # <img ... src="/vault/0000/1205.jpg"
    # But sometimes, image loading is deferred until scroll makes them visible
    transient_pattern = "src=\"data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==\""
    transient_pattern2 = "<img src=\"/static/spinningred.gif\"> Loading</div>"
    slept: int = 0
    while (transient_pattern in ret or transient_pattern2 in ret) and slept < 10:
        time.sleep(0.5)
        slept += 1
        _scroll_image_div(driver)
        ret = driver.page_source

    # In html:
    # <script async="" src="https://cdnjs.cloudflare.com/ajax/libs/ol3/3.20.1/ol.js?_=1573360547716"></script>
    # In template:
    # $.getScript("https://cdnjs.cloudflare.com/ajax/libs/ol3/3.20.1/ol.js", function(){...
    # TODO: jQuery can cache, here it _on purpose_ generates a random ID
    pattern = "https://cdnjs.cloudflare.com/ajax/libs/ol3/3.20.1/ol.js?_="
    where_is_it = ret.find(pattern)
    if where_is_it != -1:
        random_part_index = where_is_it + len(pattern)
        ret = ret[:random_part_index] + "0000000000000" + ret[random_part_index + 13]

    return ret


# noinspection PyPep8Naming
def _remove_unpredictable_from_DOM(drv: WebDriver):
    """
        Some HTML elements are not predictable, map them to some fixed value
    """
    try:
        _csrf: WebElement = drv.find_element_by_id("csrf_token")
        # tok = csrf.get_attribute("value")
        drv.execute_script("document.getElementById('csrf_token').value = 'fooBarCsrf';")
    except NoSuchElementException:
        return


def _scroll_image_div(drv: WebDriver):
    """
        Images are lazy-loaded until we scroll enough to show them.
    """
    try:
        _column_right_div: WebElement = drv.find_element_by_id("column-right")
        # drv.execute_script("document.getElementById('column-right').scrollTo(2048, 2048);")
        # There is a layout trick so that the right pane scrolls with the main window
        drv.execute_script("window.scrollTo(2048, 2048);")
    except NoSuchElementException:
        return
