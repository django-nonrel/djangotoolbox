from setuptools import setup, find_packages


DESCRIPTION = "Djangotoolbox for Django-nonrel"
LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.rst').read()
except:
    pass

setup(name='djangotoolbox',
      version='1.6.2',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      author='Waldemar Kornewald',
      author_email='wkornewald@gmail.com',
      url='https://github.com/django-nonrel/djangotoolbox',
      packages=find_packages(),
      license='3-clause BSD',
      zip_safe=False,
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Environment :: Web Environment',
          'Framework :: Django',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.5',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Topic :: Database',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ],
)
