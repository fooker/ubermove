from setuptools import setup, find_packages

setup(
    name='ubermove',
    version='0.1',

    url='https://github.com/fooker/ubermove',
    license='GPLv3',
    author='Dustin Frisch',
    author_email='fooker@lab.sh',
    description='ubermove (short umv) is a mass file management tool utilizing your favorite text editor',

    install_requires=['rarfile>=2.7'],

    packages=find_packages(),
    entry_points={
        'console_scripts': ['umv=ubermove.main:main'],
    },
)
