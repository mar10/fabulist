"""
"""
from .context import fabulist


def demo_quotes():
    fab = fabulist.Fabulist()

    templates = [
        "$(Verb:ing) is better than $(verb:ing).",
        "$(Noun:an) a day keeps the $(noun:plural) away.",
        "If you want to $(verb) $(adv:#positive), $(verb) $(adv:#positive)!",
        'Confucius says: "The one who wants to $(verb) must $(verb) $(adv) the $(noun)!"',
        'Soon a $(adj) $(noun) will $(verb) $(adv) your life!"',
    ]
    for q in fab.generate_quotes(templates, count=100):
        print(q)


if __name__ == "__main__":
    demo_quotes()
