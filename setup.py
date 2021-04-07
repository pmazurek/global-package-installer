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
        'requests'
    ],
    entry_points=dict(
        console_scripts=[
            'ap = gpi.main:entrypoint_install',
            'rp = gpi.main:entrypoint_remove',
        ]
    )
)
