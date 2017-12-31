"""
"""
from .context import fabulist


def demo_quotes():
    fab = fabulist.Fabulist()

    print("get_word('verb'):")
    for i in range(3):
        print("- ", fab.get_word("verb"))

    print("Friendly warnings:")
    for i in range(3):
        print("- ", fab.get_quote("Don't $(verb) with my $(noun) or I'll $(verb) your $(noun:plural)."))

    print("Software release names:")
    for q in fab.generate_quotes("$(adj)-$(noun:#animal)", count=3):
        print("- ", q)

    print("Passwords:")
    for q in fab.generate_quotes("$(Adj)-$(Noun)-$(num:1,9999,4)", count=3):
        print("- ", q)

    print("Compare:")
    for q in fab.generate_quotes("One $(noun:=1) may be $(adj:=2), but two $(@1:plural) are $(@2:comp).", count=3):
        print("- ", q)

    print("Names:")
    template = ("My name is $(name:mr:middle)")
    for q in fab.generate_quotes(template, count=3):
        print("-", q)

    print("Introduction:")
    template = ("Friends call me $(name:#m:first:=1), you can call me $(@1:mr:middle).\n" +
                "  May I introduce you to my wife $(name:#f:mr:first) $(@1:last)?")
    for q in fab.generate_quotes(template, count=3):
        print("-", q)

    print("Compliments:")
    for q in fab.generate_quotes("You have very $(adj:#positive) $(noun:plural).", count=3):
        print("- ", q)

    print("Blessings:")
    for q in fab.generate_quotes("May your $(noun:plural) $(verb) $(adv:super:#positive).", count=3):
        print("- ", q)

    print("Fortune cookies:")
    templates = [
        "$(Verb:ing) is better than $(verb:ing).",
        "$(Noun:an) a day keeps the $(noun:plural) away.",
        "If you want to $(verb) $(adv:#positive), $(verb) $(adv:#positive)!",
        'Confucius says: "The one who wants to $(verb) must $(verb) $(adv) the $(noun)!"',
        ]
    for q in fab.generate_quotes(templates, count=5):
        print("- ", q)

    print("Functions:")
    templates = [
        "$(Verb) $(noun)",
        "Provide $(adj:#positive) $(noun:plural)",
        ]
    for q in fab.generate_quotes(templates, count=3):
        print("- ", q)

    print("Potential failures:")
    templates = [
        "$(Noun) does not $(verb) $(adv:#positive)",
        "$(Noun) $(verb:s) $(adv:#negative)"
    ]
    for q in fab.generate_quotes(templates, count=3):
        print("- ", q)

    print("Causes:")
    for q in fab.generate_quotes("$(Noun) is too $(adj)", count=3):
        print("- ", q)


if __name__ == '__main__':
    demo_quotes()
