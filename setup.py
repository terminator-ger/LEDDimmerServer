import os
from setuptools import setup, find_packages

BUILD_ID = os.environ.get("BUILD_BUILDID", "0")

setup(
    name="LEDDimmerServer",
    version="0.1" + "." + BUILD_ID,
    # Author details
    author="Michael Lechner",
    author_email="michael.lechner@t-online.de",
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=["gpiozero", "astral", "pytz", "requests", "simplejson"],
    tests_require=["pytest", "pytest-nunit", "pytest-cov"],
    extras_require={"develop": ["pre-commit", "bump2version"]},
)