# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

import re
from importlib.metadata import version

# -- Project information -----------------------------------------------------

project = "delb-existdb"
copyright = "2019-%Y, Theo Costea & Frank Sachsenheim"
author = "Theo Costea & Frank Sachsenheim"

# The full version, including alpha/beta/rc tags
release = version(project)
version = re.match(r"(^\d+\.\d+).*", release).group(1)

master_doc = "index"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
]

source_suffix = {".rst": "restructuredtext"}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

intersphinx_mapping = {
    "delb": ("https://delb.readthedocs.io/stable/", None),
    "cpython": ("https://docs.python.org", None),
}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"
html_logo = "snakesist-logo.png"
html_theme_options = {
    "navigation_with_keys": True,
    "source_repository": "https://github.com/delb-xml/delb-existdb/",
    "source_branch": "main",
    "source_directory": "docs/",
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

autodoc_default_options = {
    "inherited-members": True,
    "members": None,
    "show-inheritance": True,
    "undoc-members": True,
}

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"
pygments_dark_style = "monokai"
