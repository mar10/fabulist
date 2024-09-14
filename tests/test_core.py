""" """

import os
import tempfile

import pytest
import fabulist


class TestBasic:
    """Basic test cases."""

    def setup_method(self):
        self.fab = fabulist.Fabulist()
        self.temp_path = None

    def teardown_method(self):
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
        assert " " not in name, "name:first does not include :last"
        name = self.fab.get_name(":last")
        assert " " not in name, "name:last does not include :first"

    def test_pick(self):
        for _ in range(100):
            val = self.fab.get_quote("$(pick:foo,bar,b\,az)")
            assert val in ("foo", "bar", "b,az"), "Pick value"

            val = self.fab.get_quote("$(pick:abc)")
            assert val in ("a", "b", "c"), "Pick character"

            val = self.fab.get_quote("$(pick:!\\,\\:)")
            assert val in ("!", ",", ":"), "Pick special character"
        return

    def test_numbers(self):
        for _ in range(100):
            num = self.fab.get_quote("$(num)")
            assert 0 <= int(num) <= 99, "Default number: 0..99"

            num = self.fab.get_quote("$(num:-9,-1)")
            assert len(num) == 2
            assert num[0] == "-"

            num = self.fab.get_quote("$(num:1,999,3)")
            assert 1 <= int(num) <= 999, "Default number: 1..999"
            assert len(num) == 3, "Zeropadding"

            num = self.fab.get_quote("$(num:1,9,3)")
            assert 1 <= int(num) <= 9, "Default number: 1..9"
            assert len(num) == 3, "Zeropadding"
            assert num[0] == num[1] == "0"
        return

    def test_validations(self):
        with pytest.raises(ValueError):
            self.fab.get_word("unkonwn_type")
        with pytest.raises(ValueError):
            self.fab.get_word("noun", "unkonwn_mod")
        with pytest.raises(ValueError):
            self.fab.get_word("noun", "an:an")
        with pytest.raises(ValueError):
            self.fab.get_word("noun", "an:#animal:#animal")
        with pytest.raises(ValueError):
            self.fab.get_word("noun", "#unknown_tag")

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

    def test_lorem_sentence(self):
        fab = self.fab

        res = fab.get_lorem_sentence(entropy=0)
        assert res.startswith("Lorem ipsum")

        res = fab.get_lorem_sentence(entropy=1)
        assert res[0].isupper() and res[-1] == "."

        res = fab.get_lorem_sentence(entropy=2)
        assert res[0].isupper() and res[-1] == "."

        res = fab.get_lorem_sentence(10)
        assert res[0].isupper() and res[-1] == "."
        assert res.count(" ") == 9

        res = fab.get_lorem_sentence(dialect="pulp", entropy=0)
        assert res == "Do you see any Teletubbies in here?"

    def test_lorem_paragraph(self):
        fab = self.fab

        res = fab.get_lorem_paragraph(3, entropy=0)
        assert res.startswith("Lorem ipsum")
        assert res.count(".") == 3

        res = fab.get_lorem_paragraph(3, entropy=1)
        assert res.count(".") == 3

        res = fab.get_lorem_paragraph(3, entropy=2, keep_first=True)
        assert res.startswith("Lorem ipsum")
        assert res.count(".") == 3

        res = fab.get_lorem_paragraph(3, entropy=3, keep_first=True)
        assert res.startswith("Lorem ipsum")
        assert res.count(".") == 3

    def test_lorem_text(self):
        fab = self.fab

        res = fab.get_lorem_text(3, keep_first=True, entropy=3)
        assert res.count("\n") == 2
        assert res.startswith("Lorem ipsum")

    def test_lorem_demo(self):
        from .demo_lorem import demo_lorem

        demo_lorem()

    def test_infinite(self):
        # We can produce endless quotes
        for i, _quote in enumerate(
            self.fab.generate_quotes("$(noun)", count=None, dedupe=False)
        ):
            if i > 5000:
                break
        assert i == 5001

        # but dedupe may raise RuntimeError
        with pytest.raises(RuntimeError):
            for i, _s in enumerate(
                self.fab.generate_quotes("$(noun)", count=None, dedupe=True)
            ):
                if i > 5000:
                    break

    # def test_plurals(self):
    #     assert self.fab.get_default_word_form("plural", "holiday", ":plural") == ""
    #     assert self.fab.get_word("cowboy", ":plural") == "cowboys"
    #     assert self.fab.get_word("baby", ":plural") == "babies"


class TestLorem:
    """Test LoremGenerator and LoremDialect."""

    def setup_method(self):
        self.fab = fabulist.Fabulist()
        self.lorem = self.fab.lorem

    def teardown_method(self):
        self.lorem = None

    def test_validations(self):
        with pytest.raises(ValueError):
            list(self.lorem.generate_words(2, dialect="unknown_dialect"))

    def test_words(self):
        lorem = self.lorem
        dialect = lorem._get_lorem("ipsum")

        res = list(lorem.generate_words(3, entropy=0))
        assert len(res) == 3
        assert dialect.sentences[0].lower().startswith(res[0])

        res = list(self.lorem.generate_words(3, entropy=1))
        assert len(res) == 3

        res = list(self.lorem.generate_words(3, entropy=2))
        assert len(res) == 3

        res = list(self.lorem.generate_words(3, entropy=3))
        assert len(res) == 3

    def test_sentences(self):
        res = list(self.lorem.generate_sentences(3, entropy=0))
        assert len(res) == 3
        assert res[0].startswith("Lorem ipsum")

        res = list(self.lorem.generate_sentences(3, entropy=2, keep_first=True))
        assert len(res) == 3
        assert res[0].startswith("Lorem ipsum")

        res = list(
            self.lorem.generate_sentences(
                3, keep_first=True, words_per_sentence=(3, 10)
            )
        )
        assert len(res) == 3
        assert res[0].startswith("Lorem ipsum")

        res = list(self.lorem.generate_sentences(3, entropy=3, keep_first=True))
        assert len(res) == 3

    def test_paragraphs(self):
        res = list(self.lorem.generate_paragraphs(3, entropy=0))
        assert len(res) == 3
        assert res[0].startswith("Lorem ipsum")

        res = list(self.lorem.generate_paragraphs(3, entropy=2, keep_first=True))
        assert len(res) == 3
        assert res[0].startswith("Lorem ipsum")

    def test_infinite(self):
        # Words are flowing out like endless rain into a paper cup...
        for i, _word in enumerate(self.lorem.generate_words()):
            if i > 1000:
                break
        assert i == 1001
