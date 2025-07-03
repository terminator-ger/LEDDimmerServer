import os
from setuptools import setup, find_packages
from LEDDimmerServer.__version__ import __version__

setup(
    name="LEDDimmerServer",
    version=__version__,
    # Author details
    author="terminator",
    author_email="the.terminator.ger@gmail.com",
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=["gpiozero", "astral", "pytz", "requests", "simplejson"],
    tests_require=["pytest", "pytest-nunit", "pytest-cov"],
    extras_require={"develop": ["pre-commit", "bump2version"]},
)