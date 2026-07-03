Write a file `slugify.py` in /workspace exposing a function `slugify(text: str) -> str`.

Rules:
- Lowercase the text.
- A "slug" is made of runs of ASCII alphanumerics (`a-z`, `0-9`) joined by single hyphens.
- Any other character (punctuation, whitespace, non-ASCII letters like `é`) is a separator.
- Collapse repeated separators; no leading or trailing hyphen.
- Text with no alphanumerics returns the empty string `""`.

Examples:
- `slugify("Hello, World!")` -> `"hello-world"`
- `slugify("  a--b__c  ")` -> `"a-b-c"`
- `slugify("Café au lait")` -> `"caf-au-lait"`
- `slugify("___")` -> `""`
