import re

NON_ALPHANUMERIC = re.compile(r"[^A-Z0-9]+")
COMPANY_SUFFIXES = {"LLC", "LP", "LTD", "INC"}


def normalize_reference(value):
    return NON_ALPHANUMERIC.sub("", value.upper())


def normalize_text(value):
    return " ".join(NON_ALPHANUMERIC.sub(" ", value.upper()).split())


def normalize_name(value):
    words = normalize_text(value).split()
    if words and words[-1] in COMPANY_SUFFIXES:
        words = words[:-1]
    return " ".join(words)


def contains_words(text, phrase):
    if not phrase:
        return False
    return f" {phrase} " in f" {text} "