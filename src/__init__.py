"""Vortex - Simple local file gateway.

A zero-configuration file sharing server for local networks.
"""

from .cli import main
from .server import run_server, VortexHandler, get_local_ip
from .ui import render_directory_listing, render_layout

__all__ = [
    "main",
    "run_server",
    "VortexHandler",
    "get_local_ip",
    "render_directory_listing",
    "render_layout",
]

__version__ = "1.0.0"
