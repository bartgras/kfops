import re
from setuptools import setup

def get_requirements():
    with open('requirements.txt') as f:
        return f.read().splitlines()

def get_version():
    with open('__init__.py', 'r') as f:
        version_str = f.read()

    version = re.findall(r"^__version__ = ['\"](.*)['\"]", version_str)
    if version:
        return version[0]

    raise RuntimeError(f'__version__ not found ')

setup(name='kfops',
    version=get_version(),
    description='Kfops - simplified MLOps for Kubeflow',
    url='http://github.com/bartgras/kfops',
    author='Bart Grasza',
    author_email='bartgras@protonmail.com',
    license='Apache License 2.0',
    packages=['kfops'],
    entry_points={
        'console_scripts': ['kfc = kfops.cli:main']
    },
    install_requires=[
        get_requirements()
    ],
    include_package_data=True,
    zip_safe=False)