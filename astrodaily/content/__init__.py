"""Content library: reviewed English and Hindi wording for the engine's signals.

The engine decides what is true about a day; this package only says it in words. Snippets live in the
``content_snippets`` table (loaded from a private content repo by ``tools/import_content.py``). A card
line with no reviewed snippet falls back to the engine's own English reason, so the library can grow
without any release.
"""
