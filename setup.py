import sys
from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))


if sys.version_info < (3, 4):
    sys.exit('Sorry, Python < 3.4 is not supported')

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
      name='pysuezV2',
      version='0.2.2',
      description='Get your water consumption data from your Suez account (www.toutsurmoneau.fr or www.eau-olivet.fr)',
      long_description=long_description,
      author='jb101010-2',
      author_email='dev.julien.basson@gmail.com',
      url='https://github.com/jb101010-2/pySuez',
      download_url='https://github.com/jb101010-2/pySuez/releases/tag/0.2.1',
      package_data={'': ['LICENSE']},
      include_package_data=True,
      packages=find_packages(),
      entry_points={
          'console_scripts': [
              'pysuez = pysuez.__main__:main'
          ]
      },
      license='Apache 2.0',
      install_requires=['regex', 'requests'],
      classifiers=[
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.12',
      ]
)
