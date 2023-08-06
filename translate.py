import os
import polib
from googletrans import Translator
from termcolor import colored

def translate_po_files(directory_path: str):

    # Create a translator object
    translator = Translator()

    # Create a list of languages based on the folders in the translations directory
    languages = [f for f in os.listdir(directory_path) if os.path.isdir(os.path.join(directory_path, f))]

    # Loop through all languages
    for language in languages:

        # Create directory path for language
        language_path = os.path.join(directory_path, language, "LC_MESSAGES")

        # Rename messages.po to messages.temp
        os.system(f"mv {language_path}/messages.po {language_path}/messages.temp")

        # Translate messages.temp to messages.po
        po_file = polib.pofile(f"{language_path}/messages.temp")

        # Loop through all entries in the po file
        for entry in po_file:
            if not entry.msgstr:
                try:
                    # Translate the message using Google Translate
                    translation = translator.translate(entry.msgid, dest=language.replace("_", "-"), src="en")
                    entry.msgstr = translation.text

                    # Get the language code colored
                    language_code = colored(language, "green")
                    msgid = colored(entry.msgid, "yellow")
                    msgstr = colored(entry.msgstr, "cyan")

                    # Print the translated message
                    print(f"{language_code}: {msgid} -> {msgstr}")
                except Exception:
                    # Get the language code colored
                    error = colored("ERROR", "red")
                    language_code = colored(language, "red")
                    msgid = colored(entry.msgid, "yellow")

                    # Print the untranslated message
                    print(f"{error}: {language_code}: {msgid}")

        # Save the po file
        po_file.save(f"{language_path}/messages.po")

        # Remove messages.temp
        os.system(f"rm {language_path}/messages.temp")


if __name__ == "__main__":
    dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "app", "translations"))
    translate_po_files(dir_path)
