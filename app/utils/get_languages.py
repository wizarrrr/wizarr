from iso639 import languages
from os import path, listdir

def get_languages():
    base_dir = path.abspath(path.join(path.dirname(__file__), "../", "../"))
    language_dict = {}
    for language in listdir(path.join(base_dir, "app", "translations")):
        language_dict[language] = languages.get(alpha2=language.split("_")[0]).name

    return language_dict
