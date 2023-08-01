import os
import polib
from googletrans import Translator

def translate_po_files(directory_path: str):

    # Create a translator object
    translator = Translator()

    # Create a list of languages based on the folders in the translations directory
    languages = [f for f in os.listdir(directory_path) if os.path.isdir(os.path.join(directory_path, f))]

    # Loop through all languages
    for language in languages:

        # Language dictionary
        language_dict = {
            "en": "en",
            "zh_Hant": "zh-tw",
            "ca": "ca",
            "cs": "cs",
            "da": "da",
            "de": "de",
            "es": "es",
            "fa": "fa",
            "fr": "fr",
            "gsw": "de",
            "he": "he",
            "hr": "hr",
            "hu": "hu",
            "is": "is",
            "it": "it",
            "lt": "lt",
            "nb_NO": "no",
            "nl": "nl",
            "pl": "pl",
            "pt": "pt",
            "pt_BR": "pt",
            "ro": "ro",
            "ru": "ru",
            "sv": "sv",
            "zh_Hans": "zh-cn"
        }

        # Create directory path for language
        language_path = os.path.join(directory_path, language, "LC_MESSAGES")

        # Rename messages.po to messages.temp
        os.system(f"mv {language_path}/messages.po {language_path}/messages.temp")

        # Translate messages.temp to messages.po
        po_file = polib.pofile(f"{language_path}/messages.temp")

        # Loop through all entries in the po file
        for entry in po_file:
            if not entry.msgstr:
                # Translate the message using Google Translate
                translation = translator.translate(entry.msgid, dest=language_dict[language], src="en")
                entry.msgstr = translation.text
                print(f"Translated {entry.msgid} to {entry.msgstr}")

        # Save the po file
        po_file.save(f"{language_path}/messages.po")

        # Remove messages.temp
        os.system(f"rm {language_path}/messages.temp")


if __name__ == "__main__":
    dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "app", "translations"))
    translate_po_files(dir_path)
