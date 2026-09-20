"""Compatibility imports for the relocated web application server."""

from .web_app.server import create_server, main, make_handler

__all__ = ["create_server", "main", "make_handler"]
