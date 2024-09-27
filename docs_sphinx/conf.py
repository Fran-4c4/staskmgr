# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
sys.path.insert(0, os.path.abspath('..'))  # Ajusta este path según tu estructura de directorios
print("Current directory:", os.getcwd())


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Simple Task Manager'
copyright = '2024, Francisco R. Moreno Santana'
author = 'Francisco R. Moreno Santana'
release = '1.5.22'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # Si utilizas el estilo de docstrings Google o NumPy
    'sphinx.ext.doctest'
    , 'sphinx.ext.todo'
    , 'sphinx.ext.viewcode'
    , 'sphinx.ext.ifconfig'
    ,'sphinx.ext.autosummary'
]

master_doc = 'index'

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', ]
exclude_classes = ['DBBase']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
# Output file base name for HTML help builder.
htmlhelp_basename = 'STMGR'
# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}