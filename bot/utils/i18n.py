import json
from pathlib import Path



class I18n:
    
    """
    A simple Internationalization (i18n) manager to handle multi-language support.

    This class loads JSON translation files from a 'locales' directory and provides 
    methods to retrieve formatted strings based on a language key. It supports 
    fallback to a default language if a specific translation or language is missing.

    Attributes:
        default_lang (str): The language code to use as a fallback (default is "en").
        translations (dict): A dictionary storing loaded translation data.
    """
    
    
    def __init__(self, default_lang="en"):
        self.default_lang = default_lang
        self.translations = {}
        self.load_locales()



    
    def load_locales(self):
        
        """
        Scans the 'locales' directory and loads all JSON translation files.

        Each file should be named after its language code (e.g., 'en.json', 'it.json'). 
        The stem of the filename is used as the language key in the translations dictionary.

        Returns:
            None
        """
        
        base_path = Path("locales")
        for file in base_path.glob("*.json"):
            lang = file.stem
            with open(file, encoding="utf-8") as f:
                self.translations[lang] = json.load(f)





    
    def t(self, lang: str, key: str, **kwargs) -> str:
        
        """
        Translates a key into the specified language and formats it with provided arguments.

        Args:
            lang (str): The target language code.
            key (str): The translation key to look up.
            **kwargs: Dynamic values to be interpolated into the translation string.

        Returns:
            str: The formatted translation string, the default language version, 
                or the key itself if no translation is found.
        """
        
        data = self.translations.get(lang) or self.translations[self.default_lang]
        text = data.get(key) or self.translations[self.default_lang].get(key) or key
        return text.format(**kwargs)

translator = I18n(default_lang="en")



def t(lang: str, key: str, **kwargs):

    """
    Global helper function to access the translator instance more easily.

    Args:
        lang (str): The target language code.
        key (str): The translation key.
        **kwargs: Arguments for string formatting.

    Returns:
        str: The translated and formatted string.
    """

    return translator.t(lang, key, **kwargs)