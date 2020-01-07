import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="quicklogic_fasm",
    version="0.0.1",
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': ['qlfasm=quicklogic.qlfasm:main']
    }
)
