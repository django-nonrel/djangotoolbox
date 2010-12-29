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
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Framework :: Django',
    'Topic :: Database',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'License :: OSI Approved :: BSD License',
]

setup(name='djangotoolbox',
      packages=find_packages(exclude=('tests', 'tests.*')),
      author='Waldemar Kornewald',
      author_email='wkornewald@gmail.com',
      url='http://www.allbuttonspressed.com/projects/djangotoolbox',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      platforms=['any'],
      classifiers=CLASSIFIERS,
      install_requires=[],
      version='0.9.1',
)
