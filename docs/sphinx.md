# Sphinx documentation

## Installing Sphinx:
```console
pip install sphinx
```

## Folder Structure:


 <span id="1eb1"  data-selectable-paragraph="">📦root_folder<br> ┣ 📂docs<br> ┗ 📂src<br> ┃ ┣ 📜class1.py<br> ┃ ┣ 📜class2.py<br> ┃  ┃ ┗ 📜__init__.py</span>

 ## Step 1: Sphinx-quickstart
 Run the below command inside your docs folder
```console
sphinx-quickstart
``` 
sphinx-quickstart is an interactive tool that asks some questions about your project and then generates a complete documentation directory along with a make.bat file, which will be used later to generate HTML.

Here you need to check folders in docs, because it creates some files under sources and in documentation they use _sources. In this project i changed manually to the structure you can see in docs_sphinx.

 

## Step 2: Editing conf.py file
Check the conf.py file inside docs_sphinx.

## Step 3: Generating .rst files
Go to the parent folder sphinx_basics, and run the command:
```console
sphinx-apidoc -o docs_sphinx  tmgr/
``` 
In this command, we tell sphinx to grab our code from the source_code(tmgr) folder and output the generated .rst files in the docs_sphinx folder. 

## Step 4: Including module.rst and generating html

Now, include the generated modules.rst file in your index.rst

```python
toctree::
   :maxdepth: 2
   :caption: Contents:

   modules
```

Go to docs_sphinx folder and run next command in order to generate html. For other options check sphinx documentation.
```console
make html
``` 