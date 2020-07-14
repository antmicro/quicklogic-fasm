QuickLogic-FASM
===============

This repository contains tools, scripts and resources for generating a bitstream from the FASM files for the QuickLogic FPGAs.

Installation
------------

To install ``quicklogic_fasm`` run::

    pip3 install git+https://github.com/antmicro/quicklogic-fasm.git

Generating bitstream for QuickLogic from FASM
---------------------------------------------

To generate a bitstream from FASM file, you need to run::

    qlfasm <input.fasm> <output.bin>

Generating FASM from QuickLogic bitstream
-----------------------------------------

To generate a FASM file from bitstream file, you need to run::

    qlfasm -d <input.bin> <output.fasm>

Generating JLink script for Quicklogic bitstream
------------------------------------------------

To create a JLink file that can be used to flash the FPGA (i.e. for Chandalar board), you need to run::

    python -m quicklogic_fasm.bitstream_to_jlink <input.bin> <output.jlink>

Generating OpenOCD script for Quicklogic bitstream
------------------------------------------------

To create an OpenOCD file that can be used to flash the FPGA, you need to run::

    python -m quicklogic_fasm.bitstream_to_openocd <input.bin> <output.cfg>

Generating Symbiflow Database (db) files from `EOS-S3 <https://github.com/QuickLogic-Corp/EOS-S3>`_ CSV files
-------------------------------------------------------------------------------------------------------------

To generate a new FASM database, you should clone this repository::

    git clone https://github.com/antmicro/quicklogic-fasm.git
    cd quicklogic-fasm

After this, you can use ``gen_database.sh`` script that will run ``convert_csv_to_db.py`` script for all CSV files from EOS-S3 submodule::

    ./gen_database.sh <output-db-dir>

DB files from ``quicklogic_fasm/ql732b`` are the result of this script.
