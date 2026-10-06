"""A second worked example: a brief on a company before you write to it, where every signal opens to its quote."""

from .pipeline import Brief, build_brief, names_a_person, pick_pages
from .render import panel_text, render_html

__all__ = ["Brief", "build_brief", "names_a_person", "panel_text", "pick_pages", "render_html"]
