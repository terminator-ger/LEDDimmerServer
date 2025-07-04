from setuptools import setup, find_packages

setup(
    name="LEDDimmerServer",
    use_scm_version=True,
    # Author details
    author="terminator",
    author_email="the.terminator.ger@gmail.com",
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=["gpiozero", "astral", "pytz", "requests", "simplejson"],
    tests_require=["unittest", "coverage"]
)