from setuptools import setup

setup(
    name='gpi',
    version='0.1',
    url='',
    description='',
    download_url='',
    author='Piotr Mazurek',
    packages=['gpi'],
    install_requires=[
        ''
    ],
    entry_points=dict(
        console_scripts=[
            'gpi = gpi.main:entrypoint',
            'ap = gpi.main:entrypoint',
        ]
    )
)
