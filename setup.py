import setuptools

with open("README.rst", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="quicklogic_fasm",
    version="0.0.1",
    packages=setuptools.find_packages(),
    long_description=long_description,
    url="https://github.com/antmicro/quicklogic-fasm",
    author="Antmicro Ltd.",
    author_email="contact@antmicro.com",
    entry_points={
        'console_scripts': ['qlfasm=quicklogic_fasm.qlfasm:main']
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    install_requires = [
        'fasm @ git+https://github.com/symbiflow/fasm#egg=fasm',
        'fasm-utils @ git+https://github.com/QuickLogic-Corp/quicklogic-fasm-utils#egg=fasm-utils'
    ],
)
