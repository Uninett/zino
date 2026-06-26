# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import datetime
import os.path
import sys

project = 'Zino'
copyright = f'2024-{datetime.date.today().year}, Sikt - The Norwegian Agency for Shared Services in Education and Research'
author = 'Morten Brekkevold, Johanna England, Simon Tveit'
try:
    sys.path.insert(0, os.path.join(os.path.abspath('..'), 'src'))
    from zino.version import version

    release = version
except ImportError:
    version = 'dev'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.intersphinx',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
# Alabaster renders the sidebar logo from this theme option, not from
# Sphinx's html_logo. Set the logo the new theme's way if you switch themes.
html_theme_options = {
    'logo': 'zino-logo.svg',
    'logo_name': False,  # wordmark already includes the project name
}
