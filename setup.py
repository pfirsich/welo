from setuptools import setup

setup(name='welo',
    version='0.1',
    description='Command line weight loss/calorie tracker.',
    url='https://github.com/pfirsich/welo',
    author='Joel Schumacher',
    author_email='',
    license='MIT',
    packages=['welo'],
    install_requires=[
        "requests",
        "appdirs",
    ],
    entry_points = {
        'console_scripts': ['welo=welo:main'],
    },
    zip_safe=True)
