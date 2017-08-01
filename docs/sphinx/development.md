# Development

## Status and Contribution

This is hobby project in its early phase. I am not planning to invest vast efforts here, but
I am curious to get your feedback.<br>
If you like to contribute, here's what you can do:

- You use this software and like it?<br>
  Please let me know (and send your cool templates).

- Missing some words, irregular word forms, or tags?<br>
  [Edit the word lists](https://github.com/mar10/fabulist/tree/master/fabulist/data)
  and send a pull request.<br>
  NOTE: this is not about collecting as much words as possible, so do not simply dump the
  [wordnet database](http://wordnet.princeton.edu) here!
  Instead we should try to have frequently used words, with high quality tagging. Get in touch if
  you are in doubt.<br>
  [This little script](https://github.com/mar10/fabulist/blob/master/tests/list_importer.py)
  may help to merge word-lists or tags into the existing data base.

- Have an idea for improvement?<br>
  Let me know, but be prepared to invest some of your own time as well.

- Found a bug?<br>
  Keep it, or send a pull request ;-)


## Run Tests

If you plan to debug or contribute, install to run directly from the source:

	$ python setup.py develop
	$ python setup.py test

The use of `virtualenv <https://virtualenv.pypa.io/en/latest/>`_ is recommended.


## How to Contribute

Work in a virtual environment. I recommend to use [pipenv](https://github.com/kennethreitz/pipenv)
to make this easy.
Create and active the virtual environment:
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
$ python setup.py sdist bdist_wheel
$ twine upload
```


## Data Model and File Format

Empty lines and lines starting with '#' are ignored.
Attributes are comma separated. Multi-value attributes are separated by '|'.
Attributes should be omitted if they can be generated using standard rules (e.g. plural of 'cat' is 'cats').
An attribute value of '-' can be used to prevent this value (e.g. 'blood' has no plural form).

Example:
```
# Noun list
# lemma | plural | tags
blood,-,
cat,,animal|pet
...
```
