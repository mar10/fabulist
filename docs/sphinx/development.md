# Development

## Status and Contribution

This is hobby project in its early phase. I am not planning to invest vast efforts here, but
I am curious to get your feedback.<br>
If you like to contribute, here's what you can do:

- You use this software and like it?<br>
  Please let me know (and send your cool templates).

- Missing some words, irregular word forms, or tags?<br>
  [Edit the word lists](https://github.com/mar10/fabulist/tree/main/fabulist/data)
  and send a pull request.<br>
  NOTE: this is not about collecting as much words as possible, so do not simply dump the
  [wordnet database](http://wordnet.princeton.edu) here!
  Instead we should try to have frequently used words, with high quality tagging. Get in touch if
  you are in doubt.<br>
  [This little script](https://github.com/mar10/fabulist/blob/main/tests/list_importer.py)
  may help to merge word-lists or tags into the existing data base.

- Have an idea for improvement?<br>
  Let me know, but be prepared to invest some of your own time as well.

- Found a bug?<br>
  Keep it, or send a pull request ;-)


## Run Tests

If you plan to debug or contribute, install to run directly from the source:

	$ python setup.py develop
	$ python setup.py test


## How to Contribute

Work in a virtual environment. I recommend to use [pipenv](https://github.com/kennethreitz/pipenv)
to make this easy.
Create and activate the virtual environment:
```
$ cd /path/fabulist
$ pipenv shell
$ pip install -r requirements-dev.txt
$ python setup.py test
$ python setup.py develop
$ python setup.py sphinx
```

Make a release:
```
$ python setup.py test
$ python setup.py bdist_wheel
$ twine upload
```


## Data Model and File Format

### Word List Entries

Word lists are represented per word type as objects (derived from the common `_WordList` base class).<br>
A word list knows its CSV format and provides methods to load, save, and access data.<br>
The main attributes are

<dl>
  <dt>key_list</dt>
  <dd>A list of all known words in their base form (aka 'lemma').</dd>
  <dt>data</dt>
  <dd>A dictionary of additional data per lemma, stored as *word entry* dictionary.</dd>
  <dt>tag_map</dt>
  <dd>A dictionary of lemma-sets per tag.</dd>
</dl>

Word entries contain information about one single word. For example a word entry for a *noun* may look like this:
```py
{"lemma": "alpaca",
 "plural": "alpacas",
 "tags": {"animal"},  # A set of tag names or None
 }
```
**Note:** Nouns without plural form store `"plural": False`.

A word entry for a *verb* may look like this:
```py
{"lemma": "strive",
 "past": "strove",
 "pp": "striven",    # past perfect form
 "s": "strives",     # -s form
 "ing": "striving",  # -ing form
 "tags": None,       # A set of tag names or None
 }
```

A word entry for an *adjective* may look like this:
```py
{"lemma": "bad",
 "comp": "worse",       # comparative
 "super": "worst",      # superlative
 "antonym": "good",     # antonym or None
 "tags": {"negative"},  # A set of tag names or None
 }
```
**Note:** Incomparable adjectives / adverbs (e.g. 'pregnant') store `"comp": False`.


### Word List Files

Word lists are provided as plain text files in CSV format:

  - File name is `<word-type>_list.txt`.
  - Use UTF-8 encoding.
  - Empty lines and lines starting with '#' are ignored.
  - Attributes are comma separated.
  - Multi-value attributes are separated by '|'.
  - Attributes should be omitted if they can be generated using standard rules (e.g. plural of 'cat' is 'cats').
  - An attribute value of '-' is used to prevent this value (e.g. 'blood' has no plural form).

Example from `noun_list.txt`:
```
# Noun list
# lemma | plural | tags
blood,-,
cat,,animal|pet
...
```

### Lorem Ipsum Files

Blind text sources are stored as plain text files.

- File name is `lorem_<dialect>.txt`.
- Use UTF-8 encoding.
- One sentence per line.
- Paragraphs are separated by a line containing of three hyphens (`---`).

**Note:** Sentences and paragraphs are considered by API methods depending on the `entropy` argument.

Example from `lorem_ipsum.txt`:
```
# Lorem ipsum
# Opera sine nomine scripta

Lorem ipsum dolor sit amet, consectetur adipisici elit, sed eiusmod tempor incidunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquid ex ea commodi consequat.
Quis aute iure reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
---
Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse
...
```

## Name Lists

The name generator is implemented by the `NameList` class, which is virtual implementation that internally uses a `FirstnameList` and a `LastnameList` class.
The name pools are stored in `firstname_list.txt` and `lastname_list.txt` respectively. First names also use the tags `f`and `m` to denote female and/or male gender.
