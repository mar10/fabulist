""" """

# ruff: noqa: T201 (`print` found)

import fabulist


def demo_lorem():
    fab = fabulist.Fabulist()

    print("\n>>> fab.get_lorem_words(10)")
    print(fab.get_lorem_words(10))

    print("\n>>> fab.get_lorem_sentence()")
    print(fab.get_lorem_sentence())

    print('\n>>> fab.get_lorem_paragraph(3, dialect="pulp", entropy=1)')
    print(fab.get_lorem_paragraph(3, dialect="pulp", entropy=1))

    print('\n>>> fab.get_lorem_paragraph(3, dialect="trappatoni")')
    print(fab.get_lorem_paragraph(3, dialect="trappatoni"))

    print('\n>>> fab.get_lorem_paragraph(3, dialect="faust")')
    print(fab.get_lorem_paragraph(3, dialect="faust"))

    print('\n>>> fab.get_lorem_paragraph(3, dialect="romeo")')
    print(fab.get_lorem_paragraph(3, dialect="romeo"))

    print("\n>>> fab.get_lorem_text(para_count=3, keep_first=True)")
    print(fab.get_lorem_text(para_count=3, keep_first=True))


if __name__ == "__main__":
    demo_lorem()
