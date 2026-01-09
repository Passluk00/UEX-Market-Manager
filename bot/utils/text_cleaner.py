import html


"""
Sanitizes and decodes a string by resolving HTML entities.

This utility takes a potentially encoded string and converts HTML entities 
back into their corresponding characters (e.g., '&amp;' becomes '&'). 
It safely handles None values by returning an empty string.

Args:
    value (str | None): The input string to be cleaned, or None.

Returns:
    str: The unescaped string, or an empty string if the input was None.
"""
def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return html.unescape(value)
