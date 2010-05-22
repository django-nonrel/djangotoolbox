from setuptools import setup, find_packages
import os

DESCRIPTION = "Djangotoolbox for Django-nonrel"

LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.rst').read()
except:
    pass

init = os.path.join(os.path.dirname(__file__), 'djangotoolbox', '__init__.py')

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Framework :: Django',
    'Topic :: Database',
    'Topic :: Software Development :: Libraries :: Python Modules',
]

setup(name='djangotoolbox',
      packages=find_packages(),
      author='Waldemar Kornewald',
      url='http://www.allbuttonspressed.com/projects/djangotoolbox',
      include_package_data=True,
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      platforms=['any'],
      classifiers=CLASSIFIERS,
      install_requires=[],
)
