# Fabulist
[![Powered by You](http://sapegin.github.io/powered-by-you/badge.svg)](http://sapegin.github.io/powered-by-you/)
[![Build Status](https://travis-ci.org/mar10/fabulist.png?branch=master)](https://travis-ci.org/mar10/fabulist)
[![Latest Version](https://img.shields.io/pypi/v/fabulist.svg)](https://pypi.python.org/pypi/fabulist/)
[![License](https://img.shields.io/pypi/l/fabulist.svg)](https://github.com/mar10/fabulist/blob/master/LICENSE)
[![Documentation Status](https://readthedocs.org/projects/fabulist/badge/?version=latest)](http://fabulist.readthedocs.org/en/latest/)


> Generate meaningful test data based on string templates.

## Usage

```
$ pip install fabulist
```

then

```py
from fabulist import Fabulist

fab = Fabulist()

templates = [
    "$(Verb:ing) is better than $(verb:ing).",
    "$(Noun:an) a day keeps the $(noun:plural) away.",
    "If you want to $(verb) $(adv), $(verb) $(adv)!",
    'Confucius says: "The one who wants to $(verb) must $(verb) $(adv) the $(noun)!"',
    ]
print("Fortune cookies:")
for q in fab.generate_quotes(templates, count=10):
    print("- ", q)
```
will produce something like
```
Fortune cookies:
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
```

[Read The Docs](http://fabulist.readthedocs.org/en/latest/) for details.
