# -*- coding: utf-8 -*-
#!/usr/bin/env python3
import codecs
import os
import re
from setuptools import setup, find_packages
NAME = 'Simple Task Manager'
PACKAGE='tmgr'

# Obtener la ruta al directorio raíz del proyecto
here = os.path.abspath(os.path.dirname(__file__))

# Leer README.md y LICENSE
with open(os.path.join(here, 'README.md')) as f:
    readme = f.read()

with open(os.path.join(here, 'LICENSE')) as f:
    license = f.read()
    
# -*- Distribution Meta -*-

re_meta = re.compile(r'__(\w+?)__\s*=\s*(.*)')
re_doc = re.compile(r'^"""(.+?)"""')   

def _add_default(m):
    attr_name, attr_value = m.groups()
    return ((attr_name, attr_value.strip("\"'")),)

def _add_doc(m):
    return (('doc', m.groups()[0]),)

def parse_dist_meta():
    """Extract metadata information from ``$dist/__init__.py``."""
    pats = {re_meta: _add_default, re_doc: _add_doc}
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, PACKAGE, '__init__.py')) as meta_fh:
        distmeta = {}
        for line in meta_fh:
            if line.strip() == '# -eof meta-':
                break
            for pattern, handler in pats.items():
                m = pattern.match(line.strip())
                if m:
                    distmeta.update(handler(m))
        return distmeta
    
def long_description():
    try:
        return codecs.open('README.rst', 'r', 'utf-8').read()
    except OSError:
        return 'Long description error: Missing README.rst file'
# -*- Requirements -*-

def _strip_comments(l):
    return l.split('#', 1)[0].strip()


def _pip_requirement(req):
    if req.startswith('-r '):
        _, path = req.split()
        return reqs(*path.split('/'))
    return [req]

def _reqs(*f):
    return [
        _pip_requirement(r) for r in (
            _strip_comments(l) for l in open(
                os.path.join(os.getcwd(), 'requirements', *f)).readlines()
        ) if r]

def reqs(*f):
    """Parse requirement file.

    Example:
        reqs('default.txt')          # requirements/default.txt
        reqs('extras', 'redis.txt')  # requirements/extras/redis.txt
    Returns:
        List[str]: list of requirements specified in the file.
    """
    return [req for subreq in _reqs(*f) for req in subreq]
    
def install_requires():
    """Get list of requirements required for installation."""
    return reqs('defaults.txt')

meta = parse_dist_meta()

setup(
    name=meta['name'],
    version=meta['version'],
    description=meta['description'],
    long_description=long_description(),
    author=meta['author'],
    author_email=meta['contact'],
    url=meta['homepage'],
    license=license,
    install_requires=install_requires(),
    packages=find_packages(exclude=('tests', 'docs','dist'))
    ,classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache 2.0 License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7'
)

