from setuptools import setup, find_packages

DESCRIPTION = "Djangotoolbox for Django-nonrel"

LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.rst').read()
except:
    pass

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
      packages=find_packages(exclude=('tests', 'tests.*')),
      author='Waldemar Kornewald',
      url='http://www.allbuttonspressed.com/projects/djangotoolbox',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      platforms=['any'],
      classifiers=CLASSIFIERS,
      install_requires=[],
)
