"""Compatibility shim for ``pip install -e .`` on legacy pip (< 22.0).

Modern pip and build backends read project metadata directly from
``pyproject.toml``; this file exists only so that older pip versions
(which require a setuptools-style entrypoint for editable installs)
also work.
"""

from setuptools import setup

setup()
