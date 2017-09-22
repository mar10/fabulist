#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
(c) 2017 Martin Wendt; see https://github.com/mar10/fabulist
Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
from __future__ import print_function

from collections import defaultdict
import os
import random
import re
import sys

from .lorem_ipsum import LoremGenerator


# Find `$(TYPE)` or `$(TYPE:MODIFIERS)`
rex_macro = re.compile("\$\(\s*(@?\w+)\s*(\:[^\)]*)?\s*\)")


# -------------------------------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------------------------------
def get_default_word_form(word_form, lemma, entry):
    """Use standard rules to compute a word form for a given lemma.

    Args:
        word_form (str): Requested wor form, e.g. 'plural', 'ing', ...
        lemma (str): The word's base form.
        entry (dict): Word's data as stored in `_WordList.data`.
    Returns:
        str: The computed word form.
    """
    word = lemma
    if word_form == "comp":
        if word[-1] in ("e", ):
            word += "r"
        elif word[-1] in ("y", ):
            word = word[:-1] + "ier"
        else:
            word += "er"

    elif word_form == "plural":
        # https://www.grammarly.com/blog/plural-nouns/
        # TODO: this is not complete and misses lots of cases.
        # Should be part of the word-list instead
        if word[-1] in ("s", "x", "z"):
            word += "es"
        elif word[-1] in ("y", ):
            word = word[:-1] + "ies"
        elif len(word) >= 3 and word[-2:] in ("ss", "sh", "ch"):
            word += "es"
        else:
            word += "s"

    elif word_form == "super":
        if word[-1] in ("e", ):
            word += "st"
        elif word[-1] in ("y", ):
            word = word[:-1] + "iest"
        else:
            word += "est"

    elif word_form == "pp":
        word = entry["past"]
    elif word_form == "s":
        word = lemma + "s"
    elif word_form == "ing":
        word = lemma + "ing"

    return word


class ApplyTemplateError(RuntimeError):
    """Raised when a template could not be resolved."""


# -------------------------------------------------------------------------------------------------
# Macro
# -------------------------------------------------------------------------------------------------
class Macro(object):
    """Parses and represents a macro with type, modifiers, tags, and references.

    Note:
        Internal use only.
    Args:
        word_type (str): The word type, e.g. "adj", "noun", ...
        modifiers (str): E.g. "plural:an"
        word_list (_WordList): The associated :class:`_WordList` instance,
            e.g. `AdvList` for word_type `adj`.
    Examples:
        $(TYPE:MODS:#foo|bar:=NUM)
    """
    def __init__(self, word_type, modifiers, word_list):
        self.word_type = word_type.lower()  #: lowercase word type ('adv', 'adj', ...)
        self.word_form = None
        self.modifiers = set()
        self.tags = set()
        self.var_name = None
        self.ref_lemma = None
        self.is_caps = word_type[0].isupper()

        has_tags = False
        if modifiers:
            modifiers = modifiers.lstrip(":")
            for m in modifiers.split(":"):
                m = m.strip().lower()
                if m.startswith("#"):
                    # Tag filter
                    if has_tags:
                        raise ValueError(
                            "Only one `:#TAGLIST` entry is allowed in macro modifiers.")
                    has_tags = True
                    for tag in m[1:].split("|"):
                        tag = tag.strip()
                        if tag in self.tags:
                            raise ValueError("Duplicate tag '{}'.".format(tag))
                        self.tags.add(tag)
                elif m.startswith("="):
                    # Variable assignment
                    if self.var_name:
                        raise ValueError(
                            "Only one `:=NUM` assignment entry is allowed in macro modifiers.")
                    self.var_name = "@{:d}".format(int(m[1:]))
                elif m:
                    # Modifier
                    if m in self.modifiers:
                        raise ValueError("Duplicate modifier '{}'.".format(m))
                    if m in word_list.form_modifiers:
                        # Word-form modifier ('plural', 'pp', 's', 'ing', ...)
                        if self.word_form:
                            raise ValueError(
                                "Only one word-form modifier is allowed '{}'."
                                .format("', '".join(word_list.form_modifiers)))
                        self.word_form = m
                    elif m in word_list.extra_modifiers:
                        # Additional modifier ('an', 'mr', ...)
                        self.modifiers.add(m)
                    else:
                        raise ValueError("Unsupported modifier: '{}'".format(m))
                else:
                    # empty modifier (`::`)
                    raise ValueError("Empty modifier: {!r}".format(modifiers))
        return

    def __str__(self):
        res = [self.word_type]
        if self.word_form:
            res.append(self.word_form)
        if self.modifiers:
            res.extend(self.modifiers)
        if self.tags:
            res.append("#" + "|".join(self.tags))
        if self.var_name:
            res.append("={}".format(self.var_name))
        return "$({})".format(":".join(res))


# -------------------------------------------------------------------------------------------------
# _WordList
# -------------------------------------------------------------------------------------------------
class _WordList(object):
    """Common base class for all word lists.

    Note:
        This class is not instantiated directly, but provides common implementations for reading,
        writing and processing of word list data.

    Args:
        path (str): Location of dictionary csv file.
    Attributes:
        path (str): Location of dictionary csv file.
        data (dict): Maps word lemmas to dicts of word data (i.e. word-forms).
        key_list (list): List of all known word lemmas.
        tag_map (dict): Maps tag names to sets of word lemmas.
    """
    word_type = None
    """str: Type of word list (e.g. 'adj', 'adv', ...). Set by derived classes."""
    csv_format = None
    """tuple: Ordered list of CSV file columns (e.g. ('lemma', 'plural', 'tags')).
    Set by derived classes."""
    computable_modifiers = frozenset()
    """frozenset: Set of word forms that can potentially be computed from a lemma
    (e.g. {'ing', 's', ...}). Set by derived classes."""
    form_modifiers = None
    """frozenset: Set of supported word form modifiers (e.g. {'plural'}).
    Set by derived classes."""
    extra_modifiers = None
    """frozenset: Set of supported additional modifiers (e.g. {'an'}). Set by derived classes."""
    all_modifiers = None
    """frozenset: Set of all supported modifiers (word-form and additional).
    Set by derived classes."""

    def __init__(self, path):
        self.path = path
        self.data = {}
        self.key_list = []
        # { tagname: set(lemma_1, lemma_2, ...) }
        self.tag_map = defaultdict(set)
        # Used to restore comments in save_as():
        self.file_comments = []

    def __str__(self):
        s = "{}(len={}, tags:{})".format(
            self.__class__.__name__, len(self.key_list), ", ".join(self.tag_map.keys()))
        return s

    def _process_entry(self, lemma, entry):
        """Expand empty values ("") if they are computable. """
        for modifier in self.computable_modifiers:
            # e.g. "super", "plural", ...
            if entry.get(modifier) is None:
                entry[modifier] = get_default_word_form(modifier, lemma, entry)

    def _un_process_entry(self, lemma, entry):
        """Squash values to `None` if they are re-computable."""
        for modifier in self.computable_modifiers:
            # e.g. "super", "plural", ...
            if (entry.get(modifier)
                    and entry[modifier] == get_default_word_form(modifier, lemma, entry)):
                entry[modifier] = None

    def _iter_file(self, path):
        """Parse a text file and yield entry-dicts."""
        csv_format = self.csv_format

        for line in open(path, "rt"):
            line = line.strip()
            if not line:
                continue
            elif line.startswith("#"):
                self.file_comments.append(line)
                continue

            entry = {}
            fields = line.split(",")
            assert len(fields) == len(csv_format), "token count mismatch in {}".format(line)
            for idx, name in enumerate(csv_format):
                value = fields[idx].strip()
                if name == "tags":
                    # Convert tags-string into a set
                    if value:
                        tag_set = entry[name] = set()
                        for tag in value.split("|"):
                            tag = tag.strip().lower()
                            tag_set.add(tag)
                    else:
                        entry[name] = None
                else:
                    if value == "-":
                        entry[name] = False
                    elif value == "":
                        entry[name] = None
                    else:
                        entry[name] = value
            yield entry
        return

    def _filter_key_list(self, tags):
        """Return key_list filtered by tags (if any)."""
        if not tags:
            return self.key_list
        matching = set()
        for tag in tags:
            if tag in self.tag_map:
                matching.update(self.tag_map[tag])
            else:
                raise ValueError(
                    "{} has no entries for tag '{}' (expected {})"
                    .format(self.__class__.__name__, tag, self.tag_map.keys()))
        return list(matching)

    def get_random_entry(self, macro):
        """Return a random entry dict, according to modifiers.

        Args:
            macro (:class:`Macro`): A parsed template macro.
        Returns:
            dict: A random entry from :attr:`key_list`.
        """
        if macro.word_type != "name":
            assert macro.word_type == self.word_type
        if not self.data:
            self.load()
        key_list = self._filter_key_list(macro.tags)
        key = random.choice(key_list)
        entry = self.data[key]
        return entry

    def apply_macro(self, macro, entry):
        """Return a word-form for an entry dict, according to macro modifiers.

        Args:
            macro (:class:`Macro`): The parsed macro instance.
            entry (dict): Dict of word forms as stored in :attr:`data`.
        Returns:
            str: The requested word form.
        """
        # print("apply_macro", macro, entry)
        if macro.word_type != "name":
            assert macro.word_type == self.word_type
        word_form = macro.word_form or "lemma"
        modifiers = macro.modifiers

        word = entry[word_form]
        if word is False:
            # For example trying to apply the `:plural` modifier on an uncountable noun
            raise ApplyTemplateError("Could not apply {} on entry {}".format(macro, entry))

        if "an" in modifiers:
            if word[0].lower() in ("a", "e", "i", "o"):
                word = "an " + word
            else:
                word = "a " + word
        return word

    def update_data(self):
        """Update internal structures after entries have been added or modified."""
        self.key_list = list(self.data.keys())

    def add_entry(self, entry):
        """Add a single entry to the word list.

        The `entry` argument should have the same keys as the current CSV file format
        (see :attr:`csv_format`).
        If `entry` values are omitted or `None`, they are passed to :meth:`_process_entry`
        in order to compute a default.
        If `entry` values are set to `False`, they are considered 'not available'. For example
        There is no `plural` form of 'information'.

        Callers should also call :meth:`update_data` later, to make sure that :attr:`key_list`
        is up-to-date.

        Args:
            entry (dict): Word data.
        """
        lemma = entry["lemma"]
        self.data[lemma] = entry
        self._process_entry(lemma, entry)
        tags = entry.get("tags")
        if tags:
            for tag in tags:
                self.tag_map[tag].add(lemma)

    def load(self, path=None):
        """Load and add list of entries from text file.

        Normally, we don't have to call this method explicitly, because entries are loaded
        lazily on demand.
        It may be useful however to add supplemental word  lists however.

        This method also calls :meth:`update_data`.

        Args:
            path (str, optional): path to CSV file. Defaults to :attr:`path`.
        """
        if path is None:
            path = self.path

        for entry in self._iter_file(path):
            self.add_entry(entry)
        self.update_data()
        # print("Loaded {}".format(self))

    def save_as(self, path):
        """Write current data to a text file.

        The resulting CSV file has the format as defined in :attr:`csv_format`.
        For better compression, word forms that are computable are stored as empty strings ('').
        Comments from the original file are retained at the top.

        Args:
            path (str): path to CSV file.
        """
        self.update_data()
        with open(path, "wt") as fs:
            for line in self.file_comments:
                fs.write(line + "\n")
            for lemma in sorted(self.key_list, key=str.lower):
                entry = self.data[lemma]
                # Squash values to "" if they are reproducible
                self._un_process_entry(lemma, entry)
                line = []
                for attr in self.csv_format:
                    value = entry.get(attr)
                    if attr == "tags":
                        if value:
                            value = "|".join(sorted(list(value)))
                        else:
                            value = ""
                    else:
                        if value is None:
                            value = ""
                        elif value is False:
                            value = "-"

                    line.append(value)
                fs.write(",".join(line) + "\n")
        return


# -------------------------------------------------------------------------------------------------
# AdjList
# -------------------------------------------------------------------------------------------------
class AdjList(_WordList):
    """Implement a collection of adjectives.

    Args:
        path (str): Path to CSV source file (loaded on demand or when :meth:`_WordList.load`)
            is called.
    """
    word_type = "adj"
    csv_format = ("lemma", "comp", "super", "antonym", "tags")
    computable_modifiers = frozenset(("comp", "super"))
    form_modifiers = frozenset(csv_format).difference(("tags", ))
    extra_modifiers = frozenset(("an", ))
    all_modifiers = form_modifiers.union(extra_modifiers)

    def __init__(self, path):
        super(AdjList, self).__init__(path)


# -------------------------------------------------------------------------------------------------
# AdvList
# -------------------------------------------------------------------------------------------------
class AdvList(_WordList):
    """Implement a collection of adverbs.

    Args:
        path (str): Path to CSV source file (loaded on demand or when :meth:`_WordList.load`)
            is called.
    """
    word_type = "adv"
    csv_format = ("lemma", "comp", "super", "antonym", "tags")
    computable_modifiers = frozenset(("comp", "super"))
    form_modifiers = frozenset(csv_format).difference(("tags", ))
    extra_modifiers = frozenset(("an", ))
    all_modifiers = form_modifiers.union(extra_modifiers)

    def __init__(self, path):
        super(AdvList, self).__init__(path)


# -------------------------------------------------------------------------------------------------
# FirstnameList
# -------------------------------------------------------------------------------------------------
class FirstnameList(_WordList):
    """List of first names, tagged by gender.

    Internally used by :py:class:`NameList`, not intended to be instantiated directly.
    """
    csv_format = ("lemma", "tags")

    def __init__(self, path):
        super(FirstnameList, self).__init__(path)

    def update_data(self):
        """Update internal structures after entries have been added or modified."""
        super(FirstnameList, self).update_data()
        # Convert to lists for efficient access
        self.key_list_male = list(self.tag_map["m"])
        self.key_list_female = list(self.tag_map["f"])


# -------------------------------------------------------------------------------------------------
# LastnameList
# -------------------------------------------------------------------------------------------------
class LastnameList(_WordList):
    """List of last names.

    Note:
        Internally used by :py:class:`NameList`, not intended to be instantiated directly.
    """
    csv_format = ("lemma", )

    def __init__(self, path):
        super(LastnameList, self).__init__(path)


# -------------------------------------------------------------------------------------------------
# NameList
# -------------------------------------------------------------------------------------------------
class NameList(_WordList):
    """Implement a virtual collection of person names.

    Internally uses :class:`FirstnameList` and :class:`LastnameList` to generate different
    variants.

    Args:
        path (str): Path to CSV source file (loaded on demand or when :meth:`_WordList.load`)
            is called.
    Attributes:
        firstname_list (list[FirstnameList]):
        lastname_list (list[LastnameList]):
    """
    word_type = "name"
    csv_format = None
    computable_modifiers = frozenset()
    form_modifiers = frozenset()
    extra_modifiers = frozenset(("first", "last", "middle", "mr"))
    all_modifiers = form_modifiers.union(extra_modifiers)

    middle_initials = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    middle_name_probability = 0.5

    def __init__(self, path):
        assert path is None
        super(NameList, self).__init__(path)
        root = os.path.dirname(__file__)
        self.firstname_list = FirstnameList(os.path.join(root, "data/firstname_list.txt"))
        self.lastname_list = LastnameList(os.path.join(root, "data/lastname_list.txt"))

    def load(self, path=None):
        """Load and add list of entries from text file."""
        assert path is None
        self.firstname_list.load()
        self.lastname_list.load()

    def get_random_entry(self, macro):
        if not self.firstname_list.data:
            self.load()

        tags = macro.tags

        # If neither m nor f are given, assume both
        if bool("m" in tags) == bool("f" in tags):
            # If both genders are allowed, we have to randomize here, because the resulting
            # firstname may be ambigous
            is_male = bool(random.getrandbits(1))
        else:
            # The modifier contains either 'm' or 'f' (not both)
            is_male = "m" in tags

        if is_male:
            first_name_list = self.firstname_list.key_list_male
        else:
            first_name_list = self.firstname_list.key_list_female

        # We generate a complete entry from our first- and last-name lists.
        # The entry contains all values (even if they are not required by current macro)
        # in case we back-reference with other filters later:
        entry = {
            "mr": "Mr." if is_male else "Mrs.",
            "first": random.choice(first_name_list),
            "middle": "",
            "last": random.choice(self.lastname_list.key_list),
            }
        if random.random() <= self.middle_name_probability:
            entry["middle"] = random.choice(self.middle_initials) + "."

        return entry

    def apply_macro(self, macro, entry):
        # Build a name from the requested modifiers
        modifiers = macro.modifiers
        # If neither first nor last are given, assume both
        full_name = bool("first" in modifiers) == bool("last" in modifiers)

        res = []
        if "mr" in modifiers:
            res.append(entry["mr"])
        if full_name or "first" in modifiers:
            res.append(entry["first"])
        if "middle" in modifiers and entry["middle"]:
            res.append(entry["middle"])
        if full_name or "last" in modifiers:
            res.append(entry["last"])
        name = " ".join(res)
        return name


# -------------------------------------------------------------------------------------------------
# NounList
# -------------------------------------------------------------------------------------------------
class NounList(_WordList):
    """Implement a collection of nouns.

    Args:
        path (str): Path to CSV source file (loaded on demand or when :meth:`_WordList.load`)
            is called.
    """
    word_type = "noun"
    csv_format = ("lemma", "plural", "tags")
    computable_modifiers = frozenset(("plural", ))
    form_modifiers = frozenset(csv_format).difference(("tags", ))
    extra_modifiers = frozenset(("an", ))
    all_modifiers = form_modifiers.union(extra_modifiers)

    def __init__(self, path):
        super(NounList, self).__init__(path)


# -------------------------------------------------------------------------------------------------
# VerbList
# -------------------------------------------------------------------------------------------------
class VerbList(_WordList):
    """Implement a collection of verbs.

    Args:
        path (str): Path to CSV source file (loaded on demand or when :meth:`_WordList.load`)
            is called.
    """
    word_type = "verb"
    csv_format = ("lemma", "past", "pp", "s", "ing", "tags")
    computable_modifiers = frozenset(("pp", "s", "ing"))
    form_modifiers = frozenset(csv_format).difference(("tags", ))
    extra_modifiers = frozenset(("an", ))
    all_modifiers = form_modifiers.union(extra_modifiers)

    def __init__(self, path):
        super(VerbList, self).__init__(path)


# -------------------------------------------------------------------------------------------------
# Fabulist
# -------------------------------------------------------------------------------------------------
class Fabulist(object):
    """Random string factory.

    Attributes:
        list_map (list): Dictionary with one :class:`_WordList` entry per word-type.
        lorem (:class:`fabulist.lorem_ipsum.LoremGenerator`):
    """
    def __init__(self):
        root = os.path.dirname(__file__)
        data_folder = os.path.join(root, "data")
        self.lorem = LoremGenerator(data_folder)
        self.list_map = {
            "adj": AdjList(os.path.join(data_folder, "adj_list.txt")),
            "adv": AdvList(os.path.join(data_folder, "adv_list.txt")),
            "noun": NounList(os.path.join(data_folder, "noun_list.txt")),
            "verb": VerbList(os.path.join(data_folder, "verb_list.txt")),
            "name": NameList(None),
            }

    def load(self):
        """Load all word lists into memory (lazy loading otherwise)."""
        for word_list in self.list_map.values():
            word_list.load()

    def get_word(self, word_type, modifiers=None, context=None):
        """Return a random word.

        Args:
            word_type (str): For example 'adj', 'adv', 'name', 'noun', 'verb'.
            modifiers (str, optional):
                Additional modifiers, separated by ':'. Default: "".
            context (dict, optional):
                Used internally to cache template results for back-references.
        Returns:
            str: A random word of the requested type and form.
        """
        if context is None:
            context = {}
        ref_map = context.setdefault("ref_map", {})
        # Handle references to another macro, e.g. `@1:...`
        # print("get_word", word_type, modifiers, context)
        if word_type.startswith("@"):
            # print("Back-ref", word_type, ref_map)
            ref_entry = ref_map.get(word_type)
            if not ref_entry:
                raise ValueError("Reference to undefined variable: '{}'".format(word_type))
            word_type = ref_entry["word_type"]
            entry = ref_entry["entry"]
            word_list = self.list_map.get(word_type.lower())
            macro = Macro(word_type, modifiers, word_list)
            word = word_list.apply_macro(macro, entry)
            return word

        word_list = self.list_map.get(word_type.lower())
        if not word_list:
            raise ValueError("Invalid word type: '{}'".format(word_type))

        macro = Macro(word_type, modifiers, word_list)
        entry = word_list.get_random_entry(macro)
        word = word_list.apply_macro(macro, entry)
        if macro.var_name:
            if macro.var_name in ref_map:
                raise ValueError("Duplicate variable assignment: '{}'".format(macro.var_name))
            ref_map[macro.var_name] = {"entry": entry, "word_type": word_type}
        if macro.is_caps:
            word = word.capitalize()
        return word

    def _format_quote(self, template):
        assert type(template) is str
        res = template
        context = {}
        # TODO: pre-compile & cache the template somehow:
        for m in rex_macro.finditer(template):
            term, word_type, modifiers = m.group(0), m.group(1), m.group(2)
            word = self.get_word(word_type, modifiers, context)
            # Only replace one (this) match
            # print(term, word, modifiers)
            res = res.replace(term, word, 1)

        return res

    def generate_quotes(self, template, count=None, dedupe=False):
        """Return a generator for random strings.

        Args:
            template (str | str[]):
                A string template with embedded macros, e.g. "Hello $(name:mr)!".
                If a list of strings are passed, a random template is chosen.
            count (int, optional):
                Number of results to generate. Pass None for infinite.
                Default: None.
            dedupe (bool | set, optional):
                Pass `True` to prevent duplicate results. If a `set` instance is passed, it
                will be used to add and check for generated entries.
                Default: False.
        Yields:
            str: Random variants of `template`.
        """
        if dedupe is True:
            dedupe = set()

        i = 0
        fail = 0  # Prevent infinite loops
        max_fail = max(1000, 10*count) if count else 1000
        while count is None or i < count:
            fail += 1
            if fail > max_fail:
                msg = "Max fail count ({}) exceeded: produced {}/{} strings.".format(
                        max_fail, i, count, file=sys.stderr)
                raise RuntimeError(msg)

            if isinstance(template, (list, tuple)):
                t = random.choice(template)
            else:
                t = template

            try:
                q = self._format_quote(t)
            except ApplyTemplateError as e:
                print("{}".format(e), file=sys.stderr)
                continue

            if dedupe is not False:
                if q in dedupe:
                    continue
                dedupe.add(q)
            yield q
            i += 1
            fail = 0  # Reset skip counter

        return

    def get_quote(self, template):
        """Return a single random string.

        This is a convenience variant of :meth:`generate_quotes`.

        Args:
            template (str | str[]):
                A string template with embedded macros, e.g. "Hello $(name:mr)!".
                If a list of strings are passed, a random template is chosen.
        Returns:
            str: A random variant of `template`.
        """
        return next(self.generate_quotes(template, count=1, dedupe=False))

    def get_name(self, modifiers=None, context=None):
        """Return a single name string.

        This is a convenience variant of :meth:`get_word` with word_type="name".

        Args:
            modifiers (str, optional):
                Additional modifiers, separated by ':'. Default: "".
            context (dict, optional):
                Used internally to cache template results for back-references.
        Returns:
            str: A random name of the requested form.
        """
        return self.get_word("name", modifiers, context)

    def get_lorem_words(self, count=None, dialect="ipsum", entropy=3, keep_first=False):
        """Return a list of random words.

        See also :class:`fabulist.lorem_ipsum.LoremGenerator` for more flexible and efficient
        generators (accessible as :attr:`Fabulist.lorem`).

        Args:
            count (int, optional):
                Number of words. Pass None for infinite.
                Default: None.
            dialect (str, optional):
                For example "ipsum", "pulp", "trappatoni". Pass `None` to pick a random dialect.
                Default: "ipsum" (i.e. lorem-ipsum).
            entropy (int, optional):
                0: iterate words from original text
                1: pick a random paragraph, then use it literally
                2: pick a random sentence, then use it literally
                3: pick random words
                Default: 3.
            keep_first (bool, optional):
                Always return the words of the first sentence as first result.
                Default: False.
        Returns:
            list[str]:
        """
        res = self.lorem.generate_words(count, dialect, entropy, keep_first)
        return list(res)

    def get_lorem_sentence(self, word_count=(3, 15), dialect="ipsum", entropy=3):
        """Return one random sentence.

        See also :class:`fabulist.lorem_ipsum.LoremGenerator` for more flexible and efficient
        generators (accessible as :attr:`Fabulist.lorem`).

        Args:
            word_count (int or tuple(min, max), optional):
                Tuple with (min, max) number of words per sentence.
                This argument is only used for entropy=3.
                Default: (3, 15).
            dialect (str, optional):
                For example "ipsum", "pulp", "trappatoni". Pass `None` to pick a random dialect.
                Default: "ipsum" (i.e. lorem-ipsum).
            entropy (int):
                0: use first sentence from original text
                1: pick a random paragraph, then use the first sentence
                2: pick a random sentence
                3: mix random words
                Default: 3.
        Returns:
            str: One random sentence.
        """
        res = self.lorem.generate_sentences(
            1, dialect, entropy, keep_first=False, words_per_sentence=word_count)
        return next(res)

    def get_lorem_paragraph(
            self, sentence_count=(2, 6), dialect="ipsum", entropy=2, keep_first=False,
            words_per_sentence=(3, 15)):
        """Return one random paragraph.

        See also :class:`fabulist.lorem_ipsum.LoremGenerator` for more flexible and efficient
        generators (accessible as :attr:`Fabulist.lorem`).

        Args:
            sentence_count (int or tuple(min, max)):
                Number of sentences. Default: (2, 6).
            dialect (str, optional):
                For example "ipsum", "pulp", "trappatoni". Pass `None` to pick a random dialect.
                Default: "ipsum" (i.e. lorem-ipsum).
            entropy (int):
                0: iterate sentences from original text
                1: pick a random paragraph, then use it literally
                2: pick a random sentence, then use it literally
                3: pick random words
                Default: 2.
            keep_first (bool, optional):
                Always return the first sentence as first result.
                Default: False.
            words_per_sentence (int or tuple(min, max), optional):
                Number of words per sentence.
                This argument is only used for entropy=3.
                Default: (3, 15).
        Returns:
            str: One paragraph made of random sentences.
        """
        res = self.lorem.generate_paragraphs(
            1, dialect, entropy, keep_first, words_per_sentence, sentence_count)
        return next(res)

    def get_lorem_text(
            self, para_count, dialect="ipsum", entropy=2, keep_first=False,
            words_per_sentence=(3, 15), sentences_per_para=(2, 6)):
        """Generate a number of paragraphs, made up from random sentences.

        Paragraphs are seperated by newline.

        See also :class:`fabulist.lorem_ipsum.LoremGenerator` for more flexible and efficient
        generators (accessible as :attr:`Fabulist.lorem`).

        Args:
            para_count (int or tuple(min, max)):
                Number of paragraphs.
            dialect (str, optional):
                For example "ipsum", "pulp", "trappatoni". Pass `None` to pick a random dialect.
                Default: "ipsum".
            keep_first (bool, optional):
                Always return the first sentence as first result. Default: False.
            entropy (int):
                0: iterate sentences from original text
                1: pick a random paragraph, then use it literally
                2: pick a random sentence, then use it literally
                3: pick random words
                Default: 2.
            words_per_sentence (tuple(int, int), optional):
                Tuple with (min, max) number of words per sentence.
                This argument is only used for entropy=3.
                Default: (3, 15).
            sentences_per_para (tuple(int, int), optional):
                Tuple with (min, max) number of sentences per paragraph.
                Default: (2, 6).
        Returns:
            str: Text made of one or more paragraphs.
        """
        res = self.lorem.generate_paragraphs(
            para_count, dialect, entropy, keep_first, words_per_sentence, sentences_per_para)
        return "\n".join(res)
