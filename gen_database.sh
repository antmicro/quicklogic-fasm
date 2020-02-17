#!/bin/bash

DEV=ql732b
SCRIPT=./quicklogic_fasm/convert_csv_to_db.py
DEVICEXML="./EOS-S3/Device Architecture Files/QLAL4S3B.xml"
CSVLOCDIR="./EOS-S3/Configuration Bitstream Files"


CSVLOC=${CSVLOCDIR%/}

if [[ -z "${1:-}" ]]; then
   echo "Usage: $0 <out_dir>"
   exit 1
fi

OUTDIR=${1%/}

mkdir -p $OUTDIR
rm -rf $OUTDIR/*

python3 $SCRIPT "$CSVLOC/DeviceMacroCoord_$DEV.csv" "$OUTDIR/macro.db" \
   --include \
       "$CSVLOC/macroTable_$DEV.csv" \
       "$CSVLOC/macro_clkTable_$DEV.csv" \
       "$CSVLOC/macro_gclkTable_$DEV.csv" \
       "$CSVLOC/macro_interfaceTable_$DEV.csv" \
       "$CSVLOC/macro_interface_topTable_$DEV.csv" \
       "$CSVLOC/macro_interface_top_rightTable_$DEV.csv" \
       "$CSVLOC/macro_interface_top_leftTable_$DEV.csv" \
       "$CSVLOC/macro_interface_rightTable_$DEV.csv" \
       "$CSVLOC/macro_interface_leftTable_$DEV.csv" \
   --macro-names \
       macro \
       macro_clk \
       macro_gclk \
       macro_interface \
       macro_interface_top \
       macro_interface_top_right \
       macro_interface_top_left \
       macro_interface_right \
       macro_interface_left \
   --techfile "$DEVICEXML" \
   --routing-bits-outfile "$OUTDIR/macro-routing.db"

python3 $SCRIPT "$CSVLOC/ColClk_$DEV.csv" "$OUTDIR/colclk.db"
python3 $SCRIPT "$CSVLOC/TestMacro_$DEV.csv" "$OUTDIR/testmacro.db"
