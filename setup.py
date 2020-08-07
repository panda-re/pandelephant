import setuptools

with open("README.md", "r") as readme:
    long_description = readme.read()

setuptools.setup(
    name="pandelephant", # Replace with your own username
    version="0.0.1",
    author="",
    author_email="",
    description="A library for working with the PANDA database",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/panda-re/pandelephant",
    package_dir={'pandelephant': 'src'},
    packages = ['pandelephant'],
    python_requires='>=3.6',
    install_requires=['sqlalchemy'],
    extras_require={
        'postgres': ["psycopg2"]
    }
)