from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='pandelephant',
    version='0.0.2',
    description="A library for translating data from plogs to an ORM and accessing the data in the ORM",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Andrew Fasano, Andy Davis, and Tim Leek',
    author_email='fasano@mit.edu',
    url='https://github.com/panda-re/pandelephant/',
    packages=find_packages(),
    install_requires=['sqlalchemy', 'pandare'],
    python_requires='>=3.6',
    extras_require={
        'postgres': ["psycopg2"]
    }
   )
