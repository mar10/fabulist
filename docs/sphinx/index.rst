.. fabulist documentation master file, created by
	 sphinx-quickstart on Sun May 24 20:50:55 2015.
	 You can adapt this file completely to your liking, but it should at least
	 contain the root `toctree` directive.

.. _main-index:

########
Overview
########

*Generate meaningful test data based on string templates.*

:Project:   https://github.com/mar10/fabulist/
:License:   `The MIT License <https://raw.github.com/mar10/fabulist/master/LICENSE>`_
:Author:    Martin Wendt
:Version:   |version|
:Date:      |today|


.. toctree::
	 :hidden:

	 self
	 installation.md
	 user_guide.md
	 reference_guide
	 development.md
	 changes


|powered_badge| |nbsp| |travis_badge| |nbsp| |pypi_badge| |nbsp| |lic_badge| |nbsp| |rtd_badge|


Status
======

This is hobby project in its early phase. I am not planning to invest vast efforts here,
but I am curious to get your feedback.


Features
========

* Create random words, terms, or sentences based on templates
* Pick words by word type (*noun*, *adj*, ...),
  word form (*'ing'-form*, *comparative*, *plural*, ...),
  or tag (*#animal*, *#positive*, ...)
* Generate random names
* (**TODO**) Generate random texts (lorem et al)


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
	>>> fab.get_word("name", "mr:middle")
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

Read the `User Guide <user_guide.html>`_ for details.


.. |powered_badge| image:: https://sapegin.github.io/powered-by-you/badge.svg
	 :alt: Build Status
	 :target: http://sapegin.github.io/powered-by-you/

.. |travis_badge| image:: https://travis-ci.org/mar10/fabulist.png?branch=master
	 :alt: Build Status
	 :target: https://travis-ci.org/mar10/fabulist

.. |pypi_badge| image:: https://img.shields.io/pypi/v/fabulist.svg
	 :alt: PyPI Version
	 :target: https://pypi.python.org/pypi/fabulist/

.. |dl_badge| image:: https://img.shields.io/pypi/dm/fabulist.svg
	 :alt: Downloads
	 :target: https://pypi.python.org/pypi/fabulist/

.. |lic_badge| image:: https://img.shields.io/pypi/l/fabulist.svg
	 :alt: License
	 :target: https://raw.github.com/mar10/fabulist/master/LICENSE

.. |rtd_badge| image:: https://readthedocs.org/projects/fabulist/badge/?version=latest
	 :target: http://fabulist.readthedocs.org/en/latest/
	 :alt: Documentation Status

.. |nbsp| unicode:: 0xA0
	 :trim:
