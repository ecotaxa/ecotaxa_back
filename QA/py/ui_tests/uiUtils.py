import re
import time
from typing import List, Union

from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement


class MyDriver(object):
    """
    Small encapsulation of selenium driver
    """

    def __init__(self, driver: WebDriver, base_url: str):
        self.drv = driver
        self.base = base_url

    def get(self, page: str):
        """
        Go to specified page
        """
        self.drv.get(self.base + page)

    def do_input(self, dialog: Union[List[dict], dict]):
        """
            Fill-in a form and submit it, repeated if dialog is a list.
        """
        if dialog is None:
            return
        if isinstance(dialog, list):
            for a_dialog in dialog:
                self._do_input(a_dialog)
        else:
            self._do_input(dialog)

    def _do_input(self, dialog: dict):
        """
            Fill-in a form and submit it.
        """
        # Simply send keys to the HTML element
        # This way no need to worry about input type (text, checkbox, select, ...)
        last_elem = None
        for elem_id, value in dialog.items():
            elem: WebElement = self.drv.find_element_by_id(elem_id)
            elem.send_keys(value)
            last_elem = elem
        # Find the enclosing form and submit it
        last_elem.submit()

    def do_check(self, check: dict):
        """
            Check that the element pointed at contains the expected text.
        """
        if check is None:
            return
        # Verify visual value of each given element in page
        for elem_id, value in check.items():
            elem: WebElement = self.drv.find_element_by_id(elem_id)
            elem_val = elem.text
            if hasattr(value, 'match'):
                # If it's a RE then match it
                assert re.match(value, elem_val)
            else:
                # Plain equality
                assert elem_val == value

    def find_element_by_id(self, id_: str) -> WebElement:
        ret = self.drv.find_element_by_id(id_)
        return ret

    def find_element_by_class(self, clazz: str) -> WebElement:
        ret = self.drv.find_element_by_class_name(clazz)
        return ret

    def wait_for_div_appears(self, clazz: str = None, id_: str = None):
        waited = 0
        while True:
            try:
                if clazz:
                    _div = self.drv.find_element_by_class_name(clazz)
                elif id_:
                    _div = self.drv.find_element_by_id(id_)
            except NoSuchElementException:
                time.sleep(0.5)
                waited += 1
            break

    def wait_for_div_contains(self, some_text: str, clazz: str = None, id_: str = None):
        waited = 0
        while True:
            try:
                # TODO: Dup code
                if clazz:
                    div = self.drv.find_element_by_class_name(clazz)
                elif id_:
                    div = self.drv.find_element_by_id(id_)
                else:
                    raise Exception("Bad usage")
                elem_val: str = div.text
                if some_text in elem_val:
                    return
            except NoSuchElementException:
                pass
            except StaleElementReferenceException:
                # Caused sometimes by the div.text
                pass
            time.sleep(0.5)
            waited += 1

    def wait_for_div_disappears(self, clazz: str):
        waited = 0
        while True:
            try:
                _div = self.drv.find_element_by_class_name(clazz)
            except NoSuchElementException:
                break
            time.sleep(0.5)
            waited += 1
