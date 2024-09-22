.. fabulist documentation master file, created by
	 sphinx-quickstart on Sun May 24 20:50:55 2015.
	 You can adapt this file completely to your liking, but it should at least
	 contain the root `toctree` directive.

.. _main-index:

########
Overview
########

*Generate random strings that make sense.*

:Project:   https://github.com/mar10/fabulist/
:Version:   |version|, |today|

.. :License:   `The MIT License <https://github.com/mar10/fabulist/blob/main/LICENSE.txt>`_
.. :Author:    Martin Wendt

.. toctree::
	 :hidden:

	 self
	 installation.md
	 user_guide.md
	 reference_guide
	 development.md
	 changes


|powered_badge| |nbsp| |pypi_badge| |nbsp| |gha_badge| |nbsp| |coverage_badge| |nbsp| 
|lic_badge| |nbsp| |rtd_badge| |nbsp| |so_badge|


Features
========

* Create random words, terms, or sentences based on templates.
* Pick words by word type (*noun*, *adj*, ...),
  word form (*'ing'-form*, *comparative*, *plural*, ...),
  or tag (*#animal*, *#positive*, ...).
* Generate random names.
* Generate blind text (lorem-ipsum et al).

.. note::
	Unlike other libraries, Fabulist focuses on generating strings with a pseudo-semantic,
	by supporting a simple grammar. This allows to display text that is more apposite (and fun) in a
	given context.

	However, if you are looking for technical test data like email-addresses or credit-card numbers,
	have a look at `Faker <https://github.com/joke2k/faker>`_,
	`mimesis <https://github.com/lk-geimfari/mimesis>`_, and others.


Quickstart
==========

Install using pip::

	$ pip install fabulist

now the ``fabulist`` package can be used in Python code::

	$ python
	>>> from fabulist import Fabulist
	>>> fab = Fabulist()
	>>> fab.get_word("Noun")
	'Equipment'
	>>> fab.get_word("adj", "#positive")
	'kind'
	>>> fab.get_name("mr:middle")
	'Mrs. Julia P. Hughes'
	>>> fab.get_quote("Look, some $(noun:#animal:plural)!")
	'Look, some manatees!'

Running out of fortune cookies?
::

	from fabulist import Fabulist

	fab = Fabulist()

	templates = [
	    "$(Verb:ing) is better than $(verb:ing).",
	    "$(Noun:an) a day keeps the $(noun:plural) away.",
	    "If you want to $(verb) $(adv), $(verb) $(adv)!",
	    'Confucius says: "The one who wants to $(verb) must $(verb) $(adv) the $(noun)!"',
	    ]

	for q in fab.generate_quotes(templates, count=10):
	    print("- ", q)

will produce something like::

	-  A statement a day keeps the airports away.
	-  Savoring is better than magnifying.
	-  If you want to sate divisively, disuse calmly!
	-  Praying is better than inspecting.
	-  Confucius says: "The one who wants to sterilize must inform miserably the possibility!"
	-  If you want to blur orderly, stride poorly!
	-  A cost a day keeps the gears away.
	-  Subtracting is better than worshipping.
	-  If you want to damage solely, discuss jealously!
	-  Confucius says: "The one who wants to vanish must swear terribly the punch!"

Need some blind text?
::

	fab.get_lorem_paragraph(3, dialect="pulp", entropy=1)

returns a paragraph with 3 sentences:
::

	 Do you see any Teletubbies in here? Do you see a slender plastic tag clipped to my shirt with
     my name printed on it?
	 Do you see a little Asian child with a blank expression on his face sitting outside on a
     mechanical helicopter that shakes when you put quarters in it?

See also the `Intro Slides <intro_slides.html>`_
and Read the `User Guide <user_guide.html>`_ for details.


.. |powered_badge| image:: https://sapegin.github.io/powered-by-you/badge.svg
	 :alt: Build Status
	 :target: http://sapegin.github.io/powered-by-you/

.. |gha_badge| image:: https://github.com/mar10/fabulist/actions/workflows/tests.yml/badge.svg
   :alt: Build Status
   :target: https://github.com/mar10/fabulist/actions/workflows/tests.yml

.. |pypi_badge| image:: https://img.shields.io/pypi/v/fabulist.svg
   :alt: PyPI Version
   :target: https://pypi.python.org/pypi/fabulist/

.. |lic_badge| image:: https://img.shields.io/pypi/l/fabulist.svg
   :alt: License
   :target: https://github.com/mar10/fabulist/blob/main/LICENSE.txt

.. |rtd_badge| image:: https://readthedocs.org/projects/fabulist/badge/?version=latest
   :target: https://fabulist.readthedocs.io/
   :alt: Documentation Status

.. |coverage_badge| image:: https://codecov.io/github/mar10/fabulist/branch/main/graph/badge.svg?token=9xmAFm8Icl
   :target: https://app.codecov.io/github/mar10/fabulist?branch=main
   :alt: Coverage Status

.. .. |black_badge| image:: https://img.shields.io/badge/code%20style-black-000000.svg
..    :target: https://github.com/ambv/black
..    :alt: Code style: black

.. |so_badge| image:: https://img.shields.io/badge/StackOverflow-fabulist-blue.svg
   :target: https://stackoverflow.com/questions/tagged/fabulist
   :alt: StackOverflow: fabulist

.. |logo| image:: ../logo_48x48.png
   :height: 48px
   :width: 48px
   :alt: fabulist
