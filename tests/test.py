"""
"""
import os
import tempfile
import unittest

from .context import fabulist

class BasicTestSuite(unittest.TestCase):
    """Basic test cases."""
    def setUp(self):
        self.fab = fabulist.Fabulist()
        self.temp_path = None

    def tearDown(self):
        self.fab = None
        if self.temp_path:
            os.remove(self.temp_path)

    def test_basic(self):
        fab = self.fab
        word_list = fab.list_map["noun"]
        assert len(word_list.key_list) == 0
        fab.get_word("noun")
        assert len(word_list.key_list) > 0

    def test_quotes(self):
        from .demo import demo_quotes
        demo_quotes()

    def test_save(self):
        self.temp_path = tempfile.mktemp()
        wl = self.fab.list_map["adj"]
        self.fab.load()
        wl.save_as(self.temp_path)
        assert os.path.getsize(self.temp_path) > 1000


if __name__ == '__main__':
    unittest.main()
