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

license='Apache License 2.0'
# with open(os.path.join(here, 'LICENSE')) as f:
#     license = f.read()
    
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
        # return codecs.open('README.md', 'r', 'utf-8').read()
        return open('README.md').read()
    except OSError:
        return 'Long description error: Missing README.md file'
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
    resp=reqs('defaults.txt')
    # print(resp)
    # return []
    return resp

# install_requires=[
#     'SQLAlchemy>=1.4.39,<2.0.0',
#     'python-dotenv',
#     "psycopg2-binary==2.9.6; sys_platform == 'win32' and python_version >= '3.7' and python_version < '3.8'",
#     "psycopg2-binary>=2.9.6; sys_platform == 'win32' and python_version >= '3.8'",
#     "psycopg2==2.9.1; sys_platform == 'linux' and python_version >= '3.7' and python_version < '3.8'",
#     "psycopg2>=2.9.1; sys_platform == 'linux' and python_version >= '3.8'",
# ]

def packages_to_exclude():
    """Get list of requirements required for installation."""
    excludes=["docs","dist","tests", "*.tests", "*.tests.*", "tests.*"]
    return excludes


meta = parse_dist_meta()
# print("Meta data")
# print(meta)

''' 
update references
py -m pip install --upgrade pip setuptools wheel
upload to testpy 
twine upload --repository testpypi dist/* --verbose
check dist
twine check --strict dist/*
upload to pipy 
twine upload dist/* --verbose
Test pip
pip install -i https://test.pypi.org/simple/ simple-task-manager==0.1.4

'''

setup(
    name=meta['name'],
    version=meta['version'],
    description=meta['description'],
    long_description=long_description(),
    long_description_content_type='text/markdown',
    author=meta['author'],
    author_email=meta['contact'],
    url=meta['homepage'],
    project_urls={
        "Bug Tracker": meta['bug_tracker'],
        "Source Code": meta['source_code'],
    },
    license=license,
    install_requires=install_requires(),
    packages=find_packages(exclude=packages_to_exclude())
    ,classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: System :: Distributed Computing",
        "Operating System :: OS Independent"
    ],
    python_requires='>=3.7'
)

