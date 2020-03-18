#
# Description of an ecotaxa web page to test.
#


class PageToTest(object):
    """
        Information on a page to test
    """

    def __init__(self, url: str, expected_file: str):
        self.url = url
        self.expected = expected_file
        # The actions to do onto the browser after the page loading
        self.input = None
        self.after_input_check = None
        self.randoms = []

    def is_json(self):
        return self

    def then_input(self, form_input):
        """
        :param form_input: A dict with key = HTML id of the element, value = value to enter, or a list of dicts
        :return: self
        """
        self.input = form_input
        return self

    def then_check(self, page_check: dict):
        """
        :param page_check: A dict with key = HTML id of the element, value = value to check
        :return: self
        """
        self.after_input_check = page_check
        return self

    def has_random(self, random_string):
        """
            The page has this string 'sometimes', remove it _always_
        :param random_string: The string to remove
        :return: self
        """
        self.randoms.append(random_string)
        return self

    def __str__(self):
        return 'url:%s chk:%s' % (self.url, self.expected)

