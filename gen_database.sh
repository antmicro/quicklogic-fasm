#!/bin/bash

DEV=ql732b
SCRIPT=./quicklogic/convert_csv_to_db.py
CSVLOCDIR=./ql732b

CSVLOC=${CSVLOCDIR%/}

python $SCRIPT $CSVLOC/DeviceMacroCoord_$DEV.csv $1 \
   --include \
       $CSVLOC/macroTable_$DEV.csv \
       $CSVLOC/macro_clkTable_$DEV.csv \
       $CSVLOC/macro_gclkTable_$DEV.csv \
       $CSVLOC/macro_interfaceTable_$DEV.csv \
       $CSVLOC/macro_interface_topTable_$DEV.csv \
       $CSVLOC/macro_interface_top_rightTable_$DEV.csv \
       $CSVLOC/macro_interface_top_leftTable_$DEV.csv \
       $CSVLOC/macro_interface_rightTable_$DEV.csv \
       $CSVLOC/macro_interface_leftTable_$DEV.csv \
   --macro-names \
       macro \
       macro_clk \
       macro_gclk \
       macro_interface \
       macro_interface_top \
       macro_interface_top_right \
       macro_interface_top_left \
       macro_interface_right \
       macro_interface_left