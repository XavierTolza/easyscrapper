# coding=utf-8
###############################################################################
# La section avec les paramètres à changer
from glob import glob

info = dict(
    packages=["easyscrapper"],  # La liste des dossiers contenant les modules python (généralement un seul)
    # Le nom du projet python (généralement le nom du dossier unique où est stocké le projet)
    name="EasyScrapper",
    version='0.1',  # La version du code
    description='Selenium based scrapper, made for easy developments',
    # La description du paquet
    author='Xavier Tolza',  # Auteur du paquet
    author_email='tolza.xavier@gmail.com',  # email de l'auteur
)
##############################################################################

import os
import re
from multiprocessing import cpu_count
from os import listdir
from os.path import join, splitext, basename, isfile, isdir

from setuptools import setup, Extension

# On regarde si le mode debug est activé
DEBUG = os.environ.get("DEBUG")
DEBUG = DEBUG is not None and DEBUG == "1"
if DEBUG:
    print("Debug enabled")

# Reformatage du nom de projet
info["name"] = info["name"].lower().replace(" ", "_")

# En cas de compilation de code C il faut connaitre le chemin vers les librairies numpy
try:
    import numpy

    numpy_include_path = numpy.get_include()
except ImportError:
    import sys

    numpy_include_path = join(sys.executable, "site-packages/numpy/core/include/numpy")


# Compilation de code C. Cette section cherche des fichiers cython à compiler
def generate_extensions(filenames):
    extra_compile_args = ['-fopenmp']
    if DEBUG:
        extra_compile_args.append("-O0")
    extensions = []
    language = "c++"
    for base_folder in info["packages"]:
        # base_folder = abspath(base_folder)
        for i in filenames:
            extension_name = join(base_folder, i.split(".")[0]).replace("/", ".")
            extension_file = join(base_folder, i)
            if splitext(basename(i))[1] == ".pyx":
                ext = cythonize(extension_file, annotate=DEBUG, gdb_debug=DEBUG,
                                nthreads=cpu_count(), language=language)[0]
                ext.name = extension_name
            else:
                ext = Extension(extension_name, [extension_file],
                                language=language, extra_compile_args=extra_compile_args,
                                include_dirs=[numpy_include_path],
                                extra_link_args=['-fopenmp'])
            extensions.append(ext)
    return extensions


# On essaie de compiler les fichiers C et les fichiers Cython
kwargs = {}
files = sum((listdir(base_folder) for base_folder in info["packages"]), [])
try:
    from Cython.Build import cythonize

    r = re.compile(".+\.pyx")
    try:
        cython_files = [i for i in files if r.fullmatch(i) is not None]
    except AttributeError:
        cython_files = [i for i in files if r.match(i) is not None]
    if len(cython_files):
        extensions = generate_extensions(cython_files)
        kwargs.update(dict(
            ext_modules=extensions
        ))
except ImportError:
    # Cython not present, compiling C files only
    r = re.compile(".+\.c(pp)?")
    c_files = [i for i in files if r.fullmatch(i)]
    extensions = generate_extensions(c_files)
    kwargs.update(dict(
        ext_modules=extensions,
    ))

# On récupère la liste des requirements depuis le fichier requirements
requirements_file = "requirements.txt"
if isfile(requirements_file):
    with open(requirements_file, "r") as fp:
        requirements = fp.read().splitlines()
else:
    requirements = []
# On supprime les commentaires des requirements
requirements = [i for i in requirements if len(i) and i[0] != "#"]

# On transforme les requirements qui sont des urls Git
required = []
EGG_MARK = '#egg='
for line in requirements:
    if line.startswith('-e git:') or line.startswith('-e git+') or \
            line.startswith('git:') or line.startswith('git+'):
        if EGG_MARK in line:
            package_name = line[line.find(EGG_MARK) + len(EGG_MARK):]
            required.append(f"{package_name} @ {line.split(EGG_MARK)[0]}")
            # dependency_links.append(line)
        else:
            raise ValueError('Dependency to a git repository should have the format:\n'
                             'git+ssh://git@github.com/xxxxx/xxxxxx#egg=package_name')
    else:
        required.append(line)

# On ajoute les scripts
script_folder = "bin"
if isdir(script_folder):
    kwargs["scripts"] = list(glob(join(script_folder, "*")))

# On ajoute éventuellement les données
data_folder = "data"
package_data = []
for package in info["packages"]:
    package_folder = join(package, data_folder)
    if isdir(package_folder):
        for folder, _, files in os.walk(package_folder):
            package_data.append((folder.replace("%s/data" % package, package),
                                 [join(folder, file) for file in files]))
if len(package_data):
    kwargs["data_files"] = package_data

kwargs.update(info)
kwargs["install_requires"] = required
setup(**kwargs)
