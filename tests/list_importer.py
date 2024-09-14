"""
Import a plain text file, add tags to the existing words or add new words altogether.
"""
# ruff: noqa: T201 (`print` found)

import os

from fabulist import Fabulist


def merge_word_list_for_tag(src_path, dest_path=None, create_new_entries=False):
    if dest_path is None:
        dest_path = src_path + ".out"
    fab = Fabulist()
    fab.load()
    word_list = None
    for line in open(path).readlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # First line mus contain the word-type, tag-name
        if not word_list:
            word_type, tag_name = line.split(",")
            word_list = fab.list_map[word_type.strip()]
            tag_name = tag_name.strip()
            continue
        word = line
        entry = word_list.data.get(word)
        if entry:
            if tag_name:
                if entry["tags"] is None:
                    entry["tags"] = set()
                entry["tags"].add(tag_name)
                print("Add tag {!r} to {!r}: {}".format(tag_name, word, entry["tags"]))
        elif create_new_entries:
            if tag_name:
                entry = {"lemma": word, "tags": set((tag_name,))}
            else:
                entry = {"lemma": word}
            print(f"Create new entry {entry}")
            word_list.add_entry(entry)

    print(f"Saving result as {dest_path}")
    word_list.save_as(dest_path)


if __name__ == "__main__":
    path = os.path.abspath("tests/import_word_list.txt")
    merge_word_list_for_tag(path, None, False)
