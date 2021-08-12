import setuptools

with open("README.md", "r") as readme:
    long_description = readme.read()

setuptools.setup(
    name="pandelephant",
    setup_requires=['protobuf_distutils'],
    version="0.0.1",
    author="",
    author_email="",
    description="A library for working with the PANDA database",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/panda-re/pandelephant",
    package_dir={'pandelephant': 'src/pandelephant'},
    packages = ['pandelephant'],
    python_requires='>=3.6',
    install_requires=['sqlalchemy'],
    extras_require={
        'postgres': ["psycopg2-binary"]
    },
    package_data={
        'pandelephant': [
            '_data/protos/pandelephant/models.proto',
        ],
    },
    options={
        'generate_py_protobufs': {
            'source_dir':        'src/pandelephant/_data/protos',
            'output_dir':        'src',
            'proto_files':       ['pandelephant/models.proto'],
        },
    },
)
