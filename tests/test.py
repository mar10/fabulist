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

    def test_names(self):
        name = self.fab.get_name()
        assert len(name) > 2 and " " in name, "Names have first and last as default"
        name = self.fab.get_name(":first")
        assert not " " in name, "name:first does not include :last"
        name = self.fab.get_name(":last")
        assert not " " in name, "name:last does not include :first"

    def test_validations(self):
        self.assertRaises(ValueError,
            self.fab.get_word, "unkonwn_type")
        self.assertRaises(ValueError,
            self.fab.get_word, "noun", "unkonwn_mod")
        self.assertRaises(ValueError,
            self.fab.get_word, "noun", "an:an")
        self.assertRaises(ValueError,
            self.fab.get_word, "noun", "an:#animal:#animal")
        self.assertRaises(ValueError,
            self.fab.get_word, "noun", "#unknown_tag")

    def test_to_string(self):
        s = "{}".format(self.fab.list_map["adj"])
        assert s.startswith("AdjList(len=")
        nl = self.fab.list_map["noun"]
        s = "{}".format(fabulist.fabulist.Macro("noun", "an:plural:#animal", nl))
        assert s == "$(noun:plural:an:#animal)"

    def test_save(self):
        self.temp_path = tempfile.mktemp()
        wl = self.fab.list_map["adj"]
        self.fab.load()
        wl.save_as(self.temp_path)
        assert os.path.getsize(self.temp_path) > 1000


class LoremTestSuite(unittest.TestCase):
    """Test lorem-ipsium generator."""
    def setUp(self):
        self.fab = fabulist.Fabulist()

    def tearDown(self):
        self.fab = None

    def test_validations(self):
        with self.assertRaises(ValueError):
            res = list(self.fab.generate_lorem_words(2, dialect="unknown_dialect"))

    def test_words(self):
        lorem = self.fab.lorem._get_lorem("default")

        res = list(self.fab.generate_lorem_words(3, entropy=0))
        assert len(res) == 3
        assert lorem.sentences[0].lower().startswith(res[0])
        res = list(self.fab.generate_lorem_words(3, entropy=1))
        assert len(res) == 3
        res = list(self.fab.generate_lorem_words(3, entropy=2))
        assert len(res) == 3
        res = list(self.fab.generate_lorem_words(3, entropy=3))
        assert len(res) == 3

    def test_sentences(self):
        res = list(self.fab.generate_lorem_sentences(3, entropy=0))
        assert len(res) == 3
        assert res[0].startswith("Lorem ipsum")

        res = list(self.fab.generate_lorem_sentences(3, entropy=2, keep_first=True))
        assert len(res) == 3
        assert res[0].startswith("Lorem ipsum")

        res = list(self.fab.generate_lorem_sentences(3, keep_first=True, words_per_sentence=(3, 10)))
        assert len(res) == 3
        assert res[0].startswith("Lorem ipsum")

        res = list(self.fab.generate_lorem_sentences(3, entropy=3, keep_first=True))
        assert len(res) == 3

    def test_paragraphs(self):
        res = list(self.fab.generate_lorem_paragraphs(3, entropy=0))
        assert len(res) == 3
        assert res[0].startswith("Lorem ipsum")

        res = list(self.fab.generate_lorem_paragraphs(3, entropy=2, keep_first=True))
        assert len(res) == 3
        assert res[0].startswith("Lorem ipsum")


if __name__ == '__main__':
    unittest.main()
