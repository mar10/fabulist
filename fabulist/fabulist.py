#!/usr/bin/env python
"""
(c) 2017 Martin Wendt; see https://github.com/mar10/fabulist
Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""

import logging
import os
import random
import re
from collections import defaultdict

from .lorem_ipsum import LoremGenerator
from typing import Optional, Union
from collections.abc import Iterator

# Find `$(TYPE)` or `$(TYPE:MODIFIERS)`
rex_macro = re.compile(r"\$\(\s*(@?\w+)\s*(\:[^\)]*)?\s*\)")

#: The base logger (silent by default)
_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


# class FixedKeysDict(TypedDict):
#     key1: str
#     key2: int
#     key3: Optional[float]
#: A dictionary with a 'lemma' and additional values, depending on the wordlist type.
TWordListEntry = dict[str, Optional[str]]


# ------------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------------
def get_default_word_form(word_form: str, lemma: str, entry: TWordListEntry) -> str:
    """Use standard rules to compute a word form for a given lemma.

    Args:
        word_form (str): Requested word form, e.g. 'plural', 'ing', ...
        lemma (str): The word's base form.
        entry (dict): Word's data as stored in `_WordList.data`.
    Returns:
        str: The computed word form.
    """
    word = lemma
    if word_form == "comp":
        if word[-1] in ("e",):
            word += "r"
        elif word[-1] in ("y",):
            word = word[:-1] + "ier"
        else:
            word += "er"

    elif word_form == "plural":
        # https://www.grammarly.com/blog/plural-nouns/
        # TODO: this is not complete and misses lots of cases.
        # Should be part of the word-list instead
        if word[-1] in ("s", "x", "z"):
            word += "es"
        elif word[-1] in ("y",):
            if len(word) > 1 and word[-2] in ("a", "e", "i", "o", "u"):
                word += "s"
            else:
                word = word[:-1] + "ies"
        elif len(word) >= 3 and word[-2:] in ("ss", "sh", "ch"):
            word += "es"
        else:
            word += "s"

    elif word_form == "super":
        if word[-1] in ("e",):
            word += "st"
        elif word[-1] in ("y",):
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


# ------------------------------------------------------------------------------
# Macro
# ------------------------------------------------------------------------------
class Macro:
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

    def __init__(self, word_type: str, modifiers: str, word_list: "_WordList"):
        self.word_type = word_type.lower()  #: lowercase word type ('adv', 'adj', ...)
        self.word_form = None
        self.modifiers: set = set()
        self.tags: set = set()
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
                            "Only one `:#TAGLIST` entry is allowed in macro modifiers."
                        )
                    has_tags = True
                    for tag in m[1:].split("|"):
                        tag = tag.strip()
                        if tag in self.tags:
                            raise ValueError(f"Duplicate tag '{tag}'.")
                        self.tags.add(tag)
                elif m.startswith("="):
                    # Variable assignment
                    if self.var_name:
                        raise ValueError(
                            "Only one `:=NUM` assignment entry is allowed in "
                            "macro modifiers."
                        )
                    self.var_name = f"@{int(m[1:]):d}"
                elif m:
                    # Modifier
                    if m in self.modifiers:
                        raise ValueError(f"Duplicate modifier '{m}'.")
                    if m in word_list.form_modifiers:
                        # Word-form modifier ('plural', 'pp', 's', 'ing', ...)
                        if self.word_form:
                            raise ValueError(
                                "Only one word-form modifier is allowed '{}'.".format(
                                    "', '".join(word_list.form_modifiers)
                                )
                            )
                        self.word_form = m
                    elif m in word_list.extra_modifiers:
                        # Additional modifier ('an', 'mr', ...)
                        self.modifiers.add(m)
                    else:
                        raise ValueError(f"Unsupported modifier: '{m}'")
                else:
                    # empty modifier (`::`)
                    raise ValueError(f"Empty modifier: {modifiers!r}")
        return

    def __repr__(self) -> str:
        res = [self.word_type]
        if self.word_form:
            res.append(self.word_form)
        if self.modifiers:
            res.extend(self.modifiers)
        if self.tags:
            res.append("#" + "|".join(self.tags))
        if self.var_name:
            res.append(f"={self.var_name}")
        return "$({})".format(":".join(res))


# ------------------------------------------------------------------------------
# _WordList
# ------------------------------------------------------------------------------
class _WordList:
    """Common base class for all word lists.

    Note:
        This class is not instantiated directly, but provides common
        implementations for reading, writing, and processing of word list data.

    Args:
        path (str): Location of dictionary csv file.
    Attributes:
        path (str): Location of dictionary csv file.
        data (dict): Maps word lemmas to dicts of word data (i.e. word-forms).
        key_list (list): List of all known word lemmas.
        tag_map (dict): Maps tag names to sets of word lemmas.
    """

    word_type: str = None
    """str: Type of word list (e.g. 'adj', 'adv', ...). Set by derived classes."""
    csv_format: tuple = None
    """tuple: Ordered list of CSV file columns (e.g. ('lemma', 'plural', 'tags')).
    Set by derived classes."""
    computable_modifiers: frozenset = frozenset()
    """frozenset: Set of word forms that can potentially be computed from a lemma
    (e.g. {'ing', 's', ...}). Set by derived classes."""
    form_modifiers: frozenset = None
    """frozenset: Set of supported word form modifiers (e.g. {'plural'}).
    Set by derived classes."""
    extra_modifiers: frozenset = None
    """frozenset: Set of supported additional modifiers (e.g. {'an'}). 
    Set by derived classes."""
    all_modifiers: frozenset = None
    """frozenset: Set of all supported modifiers (word-form and additional).
    Set by derived classes."""

    def __init__(self, path: str):
        self.path: str = path
        self.data: dict[str, TWordListEntry] = {}
        self.key_list = []
        # { tagname: set(lemma_1, lemma_2, ...) }
        self.tag_map: dict[str, set] = defaultdict(set)
        # Used to restore comments in save_as():
        self.file_comments: list[str] = []

    def __repr__(self) -> str:
        s = "{}(len={}, tags:{})".format(
            self.__class__.__name__, len(self.key_list), ", ".join(self.tag_map.keys())
        )
        return s

    def _process_entry(self, lemma: str, entry: TWordListEntry) -> None:
        """Expand empty values ("") if they are computable."""
        for modifier in self.computable_modifiers:
            # e.g. "super", "plural", ...
            if entry.get(modifier) is None:
                entry[modifier] = get_default_word_form(modifier, lemma, entry)

    def _un_process_entry(self, lemma: str, entry: TWordListEntry) -> None:
        """Squash values to `None` if they are re-computable."""
        for modifier in self.computable_modifiers:
            # e.g. "super", "plural", ...
            if entry.get(modifier) and entry[modifier] == get_default_word_form(
                modifier, lemma, entry
            ):
                entry[modifier] = None

    def _iter_file(self, path: str) -> Iterator[TWordListEntry]:
        """Parse a text file and yield entry-dicts."""
        csv_format = self.csv_format

        for line in open(path):
            line = line.strip()
            if not line:
                continue
            elif line.startswith("#"):
                self.file_comments.append(line)
                continue

            entry = {}
            fields = line.split(",")
            assert len(fields) == len(csv_format), f"token count mismatch in {line}"
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

    def _filter_key_list(self, tags: set) -> list[str]:
        """Return key_list filtered by tags (if any)."""
        if not tags:
            return self.key_list
        matching = set()
        for tag in tags:
            if tag in self.tag_map:
                matching.update(self.tag_map[tag])
            else:
                raise ValueError(
                    f"{self.__class__.__name__} has no entries for tag '{tag}' "
                    f"(expected {self.tag_map.keys()})"
                )
        return list(matching)

    def get_random_entry(self, macro: Macro) -> TWordListEntry:
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

    def apply_macro(self, macro: Macro, entry: TWordListEntry) -> str:
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
            raise ApplyTemplateError(f"Could not apply {macro} on entry {entry}")

        if "an" in modifiers:
            if word[0].lower() in ("a", "e", "i", "o"):
                word = "an " + word
            else:
                word = "a " + word
        return word

    def update_data(self) -> None:
        """Update internal structures after entries have been added or modified."""
        self.key_list = list(self.data.keys())

    def add_entry(self, entry: TWordListEntry) -> None:
        """Add a single entry to the word list.

        The `entry` argument should have the same keys as the current CSV file format
        (see :attr:`csv_format`).
        If `entry` values are omitted or `None`, they are passed to
        :meth:`_process_entry` in order to compute a default.
        If `entry` values are set to `False`, they are considered 'not available'.
        For example There is no `plural` form of 'information'.

        Callers should also call :meth:`update_data` later, to make sure that
        :attr:`key_list` is up-to-date.

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

    def load(self, path: Optional[str] = None) -> None:
        """Load and add list of entries from text file.

        Normally, we don't have to call this method explicitly, because entries
        are loaded lazily on demand.
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

    def save_as(self, path: str) -> None:
        """Write current data to a text file.

        The resulting CSV file has the format as defined in :attr:`csv_format`.
        For better compression, word forms that are computable are stored as empty
        strings ('').
        Comments from the original file are retained at the top.

        Args:
            path (str): path to CSV file.
        """
        self.update_data()
        with open(path, "w") as fs:
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


# ------------------------------------------------------------------------------
# AdjList
# ------------------------------------------------------------------------------
class AdjList(_WordList):
    """Implement a collection of adjectives.

    Args:
        path (str):
            Path to CSV source file (loaded on demand or when
            :meth:`_WordList.load`) is called.
    """

    word_type = "adj"
    csv_format = ("lemma", "comp", "super", "antonym", "tags")
    computable_modifiers = frozenset(("comp", "super"))
    form_modifiers = frozenset(csv_format).difference(("tags",))
    extra_modifiers = frozenset(("an",))
    all_modifiers = form_modifiers.union(extra_modifiers)

    def __init__(self, path: str):
        super().__init__(path)


# ------------------------------------------------------------------------------
# AdvList
# ------------------------------------------------------------------------------
class AdvList(_WordList):
    """Implement a collection of adverbs.

    Args:
        path (str):
            Path to CSV source file (loaded on demand or when
            :meth:`_WordList.load`) is called.
    """

    word_type = "adv"
    csv_format = ("lemma", "comp", "super", "antonym", "tags")
    computable_modifiers = frozenset(("comp", "super"))
    form_modifiers = frozenset(csv_format).difference(("tags",))
    extra_modifiers = frozenset(("an",))
    all_modifiers = form_modifiers.union(extra_modifiers)

    def __init__(self, path: str):
        super().__init__(path)


# ------------------------------------------------------------------------------
# FirstnameList
# ------------------------------------------------------------------------------
class FirstnameList(_WordList):
    """List of first names, tagged by gender.

    Internally used by :py:class:`NameList`, not intended to be instantiated directly.
    """

    csv_format = ("lemma", "tags")

    def __init__(self, path: str):
        super().__init__(path)

    def update_data(self) -> None:
        """Update internal structures after entries have been added or modified."""
        super().update_data()
        # Convert to lists for efficient access
        self.key_list_male = list(self.tag_map["m"])
        self.key_list_female = list(self.tag_map["f"])


# ------------------------------------------------------------------------------
# LastnameList
# ------------------------------------------------------------------------------
class LastnameList(_WordList):
    """List of last names.

    Note:
        Internally used by :py:class:`NameList`, not intended to be instantiated
        directly.
    """

    csv_format = ("lemma",)

    def __init__(self, path: str):
        super().__init__(path)


# ------------------------------------------------------------------------------
# NameList
# ------------------------------------------------------------------------------
class NameList(_WordList):
    """Implement a virtual collection of person names.

    Internally uses :class:`FirstnameList` and :class:`LastnameList` to generate
    different variants.

    Args:
        path (str):
            Path to CSV source file (loaded on demand or when
            :meth:`_WordList.load`) is called.
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

    middle_initials: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    middle_name_probability: float = 0.5

    def __init__(self, path: str):
        assert path is None
        super().__init__(path)
        root = os.path.dirname(__file__)
        self.firstname_list = FirstnameList(
            os.path.join(root, "data/firstname_list.txt")
        )
        self.lastname_list = LastnameList(os.path.join(root, "data/lastname_list.txt"))

    def load(self, path: Optional[str] = None) -> None:
        """Load and add list of entries from text file."""
        assert path is None
        self.firstname_list.load()
        self.lastname_list.load()

    def get_random_entry(self, macro: Macro) -> TWordListEntry:
        if not self.firstname_list.data:
            self.load()

        tags = macro.tags

        # If neither m nor f are given, assume both
        if bool("m" in tags) == bool("f" in tags):
            # If both genders are allowed, we have to randomize here, because
            # the resulting firstname may be ambigous
            is_male = bool(random.getrandbits(1))
        else:
            # The modifier contains either 'm' or 'f' (not both)
            is_male = "m" in tags

        if is_male:
            first_name_list = self.firstname_list.key_list_male
        else:
            first_name_list = self.firstname_list.key_list_female

        # We generate a complete entry from our first- and last-name lists.
        # The entry contains all values (even if they are not required by current
        # macro) in case we back-reference with other filters later:
        entry = {
            "mr": "Mr." if is_male else "Mrs.",
            "first": random.choice(first_name_list),
            "middle": "",
            "last": random.choice(self.lastname_list.key_list),
        }
        if random.random() <= self.middle_name_probability:
            entry["middle"] = random.choice(self.middle_initials) + "."

        return entry

    def apply_macro(self, macro: Macro, entry: TWordListEntry) -> str:
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


# ------------------------------------------------------------------------------
# NounList
# ------------------------------------------------------------------------------
class NounList(_WordList):
    """Implement a collection of nouns.

    Args:
        path (str):
            Path to CSV source file (loaded on demand or when
            :meth:`_WordList.load`) is called.
    """

    word_type = "noun"
    csv_format = ("lemma", "plural", "tags")
    computable_modifiers = frozenset(("plural",))
    form_modifiers = frozenset(csv_format).difference(("tags",))
    extra_modifiers = frozenset(("an",))
    all_modifiers = form_modifiers.union(extra_modifiers)

    def __init__(self, path: str):
        super().__init__(path)


# ------------------------------------------------------------------------------
# VerbList
# ------------------------------------------------------------------------------
class VerbList(_WordList):
    """Implement a collection of verbs.

    Args:
        path (str):
            Path to CSV source file (loaded on demand or when
            :meth:`_WordList.load`) is called.
    """

    word_type = "verb"
    csv_format = ("lemma", "past", "pp", "s", "ing", "tags")
    computable_modifiers = frozenset(("pp", "s", "ing"))
    form_modifiers = frozenset(csv_format).difference(("tags",))
    extra_modifiers = frozenset(("an",))
    all_modifiers = form_modifiers.union(extra_modifiers)

    def __init__(self, path: str):
        super().__init__(path)


# ------------------------------------------------------------------------------
# Fabulist
# ------------------------------------------------------------------------------
class Fabulist:
    """Random string factory.

    Attributes:
        list_map (list): Dictionary with one :class:`_WordList` entry per word-type.
        lorem (:class:`fabulist.lorem_ipsum.LoremGenerator`):
    """

    def __init__(self):
        root: str = os.path.dirname(__file__)
        data_folder: str = os.path.join(root, "data")
        self.lorem: LoremGenerator = LoremGenerator(data_folder)
        self.list_map: dict[str, _WordList] = {
            "adj": AdjList(os.path.join(data_folder, "adj_list.txt")),
            "adv": AdvList(os.path.join(data_folder, "adv_list.txt")),
            "noun": NounList(os.path.join(data_folder, "noun_list.txt")),
            "verb": VerbList(os.path.join(data_folder, "verb_list.txt")),
            "name": NameList(None),
        }

    def load(self) -> None:
        """Load all word lists into memory (lazy loading otherwise)."""
        for word_list in self.list_map.values():
            word_list.load()

    def get_number(
        self, modifiers: Optional[str] = None, context: Optional[dict] = None
    ) -> str:
        """Return a string-formatted random number.

        Args:
            modifiers (str):
                Additional modifiers, separated by ':'.
                Only one modifier is accepted with a comma separated list of
                min, max, and width.
                Example: "0,99,2".

            context (dict, optional):
                Used internally to cache template results for back-references.
        Returns:
            str: A random number matching in the requested range.
        Examples:
            fab.get_number("0,999,3")
        """
        if modifiers is None:
            modifiers = "0,99,2"
        parts = modifiers.lstrip(":").split(":")
        try:
            assert len(parts) == 1
            parts = parts[0]
            parts = [int(p) for p in parts.split(",")]
            if len(parts) == 1:
                min, max, width = 0, parts[0], 0
            elif len(parts) == 2:
                min, max, width = parts[0], parts[1], 0
            else:
                min, max, width = parts
            # print("parts", min, max, width)
        except Exception as e:
            raise ValueError(
                "`num` modifier must be formatted like "
                f"'[min,]max[,width]': '{modifiers}'"
            ) from e
        num = random.randrange(min, max)
        return f"{num}".zfill(width)

    def get_choice(self, modifiers: str, context: Optional[dict] = None) -> str:
        """Return a random entry from a list of values.

        Args:
            modifiers (str):
                Additional modifiers, separated by ':'.
                Only one modifier is accepted with a comma separated list of choices.
                If a single string is passed (i.e. no comma), one random character
                is returned.
                Use a backslash to escape comma or colons.

            context (dict, optional):
                Used internally to cache template results for back-references.
        Returns:
            str: A randomly selected value.
        Examples:
            fab.get_choice("foo,bar,baz")
            fab.get_choice("$%?!")
            fab.get_choice("$%?!\\:\\,")
        """
        try:
            modifiers = modifiers.lstrip(":")
            # Split by ':' but not '\:'
            modifier_list = re.split(r"(?<!\\):", modifiers)
            modifier_list = [m.replace(r"\:", ":") for m in modifier_list]
            assert len(modifier_list) == 1
            choices = modifier_list[0]
            # print("ch2", modifiers, modifier_list, choices)
            # Split by ',' but not '\,'
            choices: list[str] = re.split(r"(?<!\\),", choices)
            if len(choices) == 1 and len(choices[0]) > 1:
                # Only one string was passed: use single characters
                choices = choices[0].replace(r"\,", ",")
                choices = tuple(choices)
            else:
                choices = [p.strip().replace(r"\,", ",") for p in choices]
        except Exception as e:
            raise ValueError(
                "`pick` modifier must be formatted like "
                f"'value[,value]*': '{modifiers}'"
            ) from e
        return random.choice(choices)

    def get_word(
        self,
        word_type: str,
        modifiers: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> str:
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
                raise ValueError(f"Reference to undefined variable: '{word_type}'")
            word_type = ref_entry["word_type"]
            entry = ref_entry["entry"]
            word_list = self.list_map.get(word_type.lower())
            macro = Macro(word_type, modifiers, word_list)
            word = word_list.apply_macro(macro, entry)
            return word

        if word_type == "num":
            return self.get_number(modifiers, context)
        elif word_type == "pick":
            return self.get_choice(modifiers, context)

        word_list = self.list_map.get(word_type.lower())
        if not word_list:
            raise ValueError(f"Invalid word type: '{word_type}'")

        macro = Macro(word_type, modifiers, word_list)
        entry = word_list.get_random_entry(macro)
        word = word_list.apply_macro(macro, entry)
        if macro.var_name:
            if macro.var_name in ref_map:
                raise ValueError(f"Duplicate variable assignment: '{macro.var_name}'")
            ref_map[macro.var_name] = {"entry": entry, "word_type": word_type}
        if macro.is_caps:
            word = word.capitalize()
        return word

    def _format_quote(self, template: str) -> str:
        assert type(template) is str, template
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

    def generate_quotes(
        self,
        template: Union[str, list[str]],
        count: Optional[int] = None,
        dedupe: Optional[bool] = False,
    ) -> Iterator[str]:
        """Return a generator for random strings.

        Args:
            template (str | str[]):
                A string template with embedded macros, e.g. "Hello $(name:mr)!".
                If a list of strings are passed, a random template is chosen.
            count (int, optional):
                Number of results to generate. Pass None for infinite.
                Default: None.
            dedupe (bool | set, optional):
                Pass `True` to prevent duplicate results. If a `set` instance is
                passed, it will be used to add and check for generated entries.
                Default: False.
        Yields:
            str: Random variants of `template`.
        """
        if dedupe is True:
            dedupe = set()

        i = 0
        fail = 0  # Prevent infinite loops
        max_fail = max(1000, 10 * count) if count else 1000
        while count is None or i < count:
            fail += 1
            if fail > max_fail:
                msg = (
                    f"Max fail count ({max_fail}) exceeded: "
                    f"produced {i}/{count} strings."
                )
                raise RuntimeError(msg)

            if isinstance(template, (list, tuple)):
                t = random.choice(template)
            else:
                t = template

            try:
                q = self._format_quote(t)
            except ApplyTemplateError as e:
                _logger.error("%s", e)
                continue

            if dedupe is not False:
                if q in dedupe:
                    continue
                dedupe.add(q)
            yield q
            i += 1
            fail = 0  # Reset skip counter

        return

    def get_quote(self, template: Union[str, list[str]]) -> str:
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

    def get_name(
        self, modifiers: Optional[str] = None, context: Optional[dict] = None
    ) -> str:
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

    def get_lorem_words(
        self,
        count: Optional[int] = None,
        dialect: Optional[str] = "ipsum",
        entropy: Optional[int] = 3,
        keep_first: Optional[bool] = False,
    ) -> list[str]:
        """Return a list of random words.

        See also :class:`fabulist.lorem_ipsum.LoremGenerator` for more flexible
        and efficient generators (accessible as :attr:`Fabulist.lorem`).

        Args:
            count (int, optional):
                Number of words. Pass None for infinite.
                Default: None.
            dialect (str, optional):
                For example "ipsum", "pulp", "trappatoni". Pass `None` to pick a
                random dialect.
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

    def get_lorem_sentence(
        self,
        word_count: Optional[Union[int, tuple[int, int]]] = (3, 15),
        dialect: Optional[str] = "ipsum",
        entropy: Optional[int] = 3,
    ) -> str:
        """Return one random sentence.

        See also :class:`fabulist.lorem_ipsum.LoremGenerator` for more flexible
        and efficient generators (accessible as :attr:`Fabulist.lorem`).

        Args:
            word_count (int or tuple(min, max), optional):
                Tuple with (min, max) number of words per sentence.
                This argument is only used for entropy=3.
                Default: (3, 15).
            dialect (str, optional):
                For example "ipsum", "pulp", "trappatoni". Pass `None` to pick a
                random dialect.
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
            1, dialect, entropy, keep_first=False, words_per_sentence=word_count
        )
        return next(res)

    def get_lorem_paragraph(
        self,
        sentence_count: Optional[Union[int, tuple[int, int]]] = (2, 6),
        dialect: Optional[str] = "ipsum",
        entropy: Optional[int] = 2,
        keep_first: Optional[bool] = False,
        words_per_sentence: Optional[Union[int, tuple[int, int]]] = (3, 15),
    ) -> str:
        """Return one random paragraph.

        See also :class:`fabulist.lorem_ipsum.LoremGenerator` for more flexible
        and efficient generators (accessible as :attr:`Fabulist.lorem`).

        Args:
            sentence_count (int or tuple(min, max)):
                Number of sentences. Default: (2, 6).
            dialect (str, optional):
                For example "ipsum", "pulp", "trappatoni". Pass `None` to pick a
                random dialect.
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
            1, dialect, entropy, keep_first, words_per_sentence, sentence_count
        )
        return next(res)

    def get_lorem_text(
        self,
        para_count: Union[int, tuple[int, int]],
        dialect: Optional[str] = "ipsum",
        entropy: Optional[int] = 2,
        keep_first: Optional[bool] = False,
        words_per_sentence: Optional[Union[int, tuple[int, int]]] = (3, 15),
        sentences_per_para: Optional[Union[int, tuple[int, int]]] = (2, 6),
    ) -> str:
        """Generate a number of paragraphs, made up from random sentences.

        Paragraphs are seperated by newline.

        See also :class:`fabulist.lorem_ipsum.LoremGenerator` for more flexible
        and efficient generators (accessible as :attr:`Fabulist.lorem`).

        Args:
            para_count (int or tuple(min, max)):
                Number of paragraphs.
            dialect (str, optional):
                For example "ipsum", "pulp", "trappatoni". Pass `None` to pick a
                random dialect.
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
            para_count,
            dialect,
            entropy,
            keep_first,
            words_per_sentence,
            sentences_per_para,
        )
        return "\n".join(res)
