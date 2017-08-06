#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
(c) 2017 Martin Wendt; see https://github.com/mar10/fabulist

Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
from __future__ import print_function

import os
# from pprint import pprint
import random


def _get_count(int_or_range):
    """Return random int for given range (or int if a simple value was passed)."""
    if type(int_or_range) is int:
        return int_or_range
    return random.randint(*int_or_range)


# -------------------------------------------------------------------------------------------------
# LoremDialect
# -------------------------------------------------------------------------------------------------
class LoremDialect(object):
    """Generate lorem ipsum text.

    Args:
        dialect (str): "lorem", "pulp", ...
        path (str):
    Examples:
        $(TYPE:MODS:#foo|bar:=NUM)
    """
    def __init__(self, dialect, path):
        self.dialect = dialect
        self.path = path
        self.paragraphs = None
        self.sentences = None
        self.words = None
        # self.load()

    def load(self):
        sentence_set = set()
        self.paragraphs = []
        self.sentences = []
        self.words = set()
        para = []
        for line in open(self.path, "rt"):
            # Skip empty lines and comments (i.e. starting with '#')
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Paragraphs are delimited by a '---' line
            if line.startswith("---"):
                self.paragraphs.append(para)
                para = []
            else:
                para.append(line)
                # Also collect a flat list of all sentences
                if line not in sentence_set:
                    self.sentences.append(line)
                    sentence_set.add(line)
                    # Also collect a set of words
                    for word in line.split(" "):
                        word = word.strip(" \t\n,.!?;:-").lower()
                        if word:
                            self.words.add(word)
        self.words = list(self.words)
        if para:
            self.paragraphs.append(para)
        # pprint(self.paragraphs)
        # pprint(self.sentences)
        # pprint(self.words)
        return

    # def generate_paragraph(self, word_count=None, keep_first=True):
    #     """Return a single string, made up of one or more sentences.
    #     Returns:
    #         A List of paragraphs,
    #     """
    #     if self.paragraphs is None:
    #         self.load()
    #     if keep_first:
    #         para = self.paragraphs[0]
    #     else:
    #         para = random.choice(self.paragraphs)
    #     paragraphs = []
    #     n = 0
    #     while n < word_count:
    #         for sentence in self.sentences:
    #             pass
    #     return s

    def _generate_sentences(self, entropy=0, keep_first=True, count=None):
        """Return
        Returns:
            A string
        """
        if self.paragraphs is None:
            self.load()

        pool_idx = 0
        pool_remain = 0
        sentence_pool = self.sentences

        n_sentences = 0
        while count is None or n_sentences < count:
            if entropy == 1 and pool_remain == 0:
                # Pick random paragraph, then use sentences in order
                sentence_pool = random.choice(self.paragraphs)
                pool_remain = len(sentence_pool)
                pool_idx = 0

            if entropy == 2:
                # Pick random sentence
                sentence = random.choice(sentence_pool)
            else:
                # Generate sentences in original order
                sentence = sentence_pool[pool_idx % len(sentence_pool)]

            if keep_first:
                keep_first = False
                if sentence != self.sentences[0]:
                    # Start with first sentence
                    yield self.sentences[0]
                    n_sentences += 1

            pool_idx += 1
            pool_remain -= 1
            n_sentences += 1

            yield sentence
        return


# -------------------------------------------------------------------------------------------------
# LoremGenerator
# -------------------------------------------------------------------------------------------------
class LoremGenerator(object):
    """Generate lorem ipsum text in a given dialect.

    Attributes:
        dialect_map (dict(dialect, LoremDialect)):
            Holds all available lorem-ipsum dialects
    """
    def __init__(self, data_folder):
        self.dialect_map = {}
        self.root_path = data_folder
        # Find all available dialects and add to map(dialect => path)
        for name in os.listdir(self.root_path):
            if name.startswith("lorem_"):
                dialect = os.path.splitext(name)[0][6:]
                path = os.path.join(self.root_path, name)
                self.dialect_map[dialect] = LoremDialect(dialect, path)
        # pprint(self.dialect_map)

    # def load(self, dialect):
    #     pass

    def _get_lorem(self, dialect):
        """Return a LoremDialect instance and load data or raise ValueError."""
        if dialect is None:
            dialect = random.choice(list(self.dialect_map.keys()))
        lorem = self.dialect_map.get(dialect)
        if not lorem:
            raise ValueError(
                "Unknown dialect {!r} (expected {})"
                .format(dialect, ", ".join(self.dialect_map.keys())))
        if lorem.paragraphs is None:
            lorem.load()
        return lorem

    def generate_words(self, count, dialect="ipsum", entropy=3, keep_first=False):
        """Yield <count> random sentences.

        Args:
            count (int):
                Number of words.
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
        Yields:
            <count> random words
        """
        lorem = self._get_lorem(dialect)
        if entropy == 3:
            # Pick random words
            if keep_first:
                raise NotImplementedError
            for _ in range(count):
                yield random.choice(lorem.words)
            return
        # Otherwise pop words from sentence sequence
        i = 0
        for s in lorem._generate_sentences(keep_first=keep_first, entropy=entropy):
            for word in s.split(" "):
                if i >= count:
                    return
                word = word.strip().strip(".!?:")
                if word:
                    yield word.lower()
                    i += 1
        return

    def generate_sentences(
            self, count, dialect="ipsum", entropy=2, keep_first=False,
            words_per_sentence=(3, 15)):
        """Yield <count> random sentences.

        Args:
            count (int):
                Number of sentences.
            dialect (str, optional):
                For example "ipsum", "pulp", "trappatoni". Pass `None` to pick a random dialect.
                Default: "ipsum" (i.e. lorem-ipsum).
            entropy (int):
                0: iterate sentences from original text
                1: pick a random paragraph, then iterate sentences
                2: pick a random sentence
                3: mix random words
                Default: 2.
            keep_first (bool, optional):
                Always return the first sentence as first result.
                Default: False.
            words_per_sentence (int or tuple(min, max), optional):
                Number of words per sentence.
                This argument is only used for entropy=3.
                Default: (3, 15).
        Yields:
            <count> random sentences
        """
        lorem = self._get_lorem(dialect)
        if entropy == 3:
            # Generate from random words
            if keep_first:
                yield lorem.sentences[0]
                count -= 1

            if not words_per_sentence:
                raise ValueError(
                    "entropy=3 requires words_per_sentence arg: int or a tuple(min, max)")

            for _ in range(count):
                n_words = _get_count(words_per_sentence)
                sentence = random.sample(lorem.words, n_words)
                sentence = " ".join(sentence).capitalize() + "."
                yield sentence
            return
        # entropy = 0..2: use sentences from original text
        for i, s in enumerate(lorem._generate_sentences(keep_first=keep_first, entropy=entropy)):
            if i >= count:
                break
            yield s
        return

    def generate_paragraphs(
            self, count, dialect="ipsum", entropy=2, keep_first=False,
            words_per_sentence=(3, 15), sentences_per_para=(2, 6)):
        """Generate a number of paragraphs, made up from random sentences.

        Args:
            count (int):
                Number of paragraphs.
            dialect (str, optional):
                For example "ipsum", "pulp", "trappatoni". Pass `None` to pick a random dialect.
                Default: "ipsum".
            keep_first (bool, optional):
                Always return the first sentence as first result. Default: False.
            entropy (int):
                0: iterate original text
                1: pick a random paragraph, then use it literally
                2: mix a random sentences
                3: mix random words
                Default: 2.
            words_per_sentence (int or tuple(min, max), optional):
                Number of words per sentence.
                This argument is only used for entropy=3.
                Default: (3, 15).
            sentences_per_para (int or tuple(min, max), optional):
                Number of sentences per paragraph.
                Default: (2, 6).
        Yields:
            <count> random paragraphs
        """
        for _ in range(count):
            n_sents = _get_count(sentences_per_para)
            para = self.generate_sentences(
                n_sents, dialect, entropy, keep_first, words_per_sentence)
            para = " ".join(para)
            yield para
            keep_first = False
        return


if __name__ == "__main__":

    data_folder = os.path.join(os.path.dirname(__file__), "data")
    lorem = LoremGenerator(data_folder)
    # print(list(lorem.generate_words(10)))
    # print(list(lorem.generate_words(10, entropy=0)))
    # print(list(lorem.generate_words(10, entropy=1)))
    # print(list(lorem.generate_words(10, entropy=2)))
    # print(list(lorem.generate_words(10, entropy=3)))
    #
    # print(list(lorem.generate_sentences(3, entropy=3, words_per_sentence=(5,8))))
    # print(list(lorem.generate_sentences(3, entropy=3, words_per_sentence=5)))
    # print(list(lorem.generate_sentences(3, entropy=3, words_per_sentence=5, keep_first=True)))
    #
    # print(list(lorem.generate_sentences(3, dialect="pulp", entropy=2, keep_first=True)))
    #
    #
    # print()
    # print("\n".join(lorem.generate_paragraphs(3)))
    # print()
    # print("\n".join(lorem.generate_paragraphs(3, dialect="pulp", entropy=2, keep_first=True)))
    # print()
    # print("\n".join(lorem.generate_paragraphs(3, dialect="pulp", entropy=3, keep_first=True)))

    exit()
    # s = lorem.generate(None, 20)
    # gen = lorem.dialect_map["pulp"].generate_sentences(3)
    gen = lorem.generate_sentences(10, keep_first=False, entropy=2)
    for s in gen:
        print("-", s)
    # s = lorem.generate("pulp", 20)
    # print(s)
