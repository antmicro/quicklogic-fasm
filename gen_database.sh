#!/bin/bash

usage() {
	echo "Usage: $0 [OPTIONS]"
	echo ""
	echo "Generate FASM database files"
	echo ""
	echo "	-d <device type>	supported devices: pp3, eos-s3"
	echo "	-o <output directory>	files inside existing directory are deleted before running the script, otherwise new directory is created"
}

while getopts d:o:h flag
do
    case "${flag}" in
        d) DEVICE=${OPTARG};;
        o) OUTDIR=${OPTARG};;
        h) usage; exit 0;;
	*) usage; 1>&2; exit 1;;
    esac
done

[ -z "$DEVICE" ] && echo "Error: -d is required argument" && RET=1
[ -z "$OUTDIR" ] && echo "Error: -o is required argument" && RET=1

if [[ $RET -eq 1 ]]; then
	usage
	exit 1
fi

if [ "$DEVICE" == "pp3" ]; then
	DEV=ql725a
	DEVICEXML="./PolarPro3/Device Architecture Files/QL3P1K.xml"
	CSVLOCDIR="./PolarPro3/Configuration Bitstream Files"
elif [ "$DEVICE" == "eos-s3" ]; then
	DEV=ql732b
	DEVICEXML="./EOS-S3/Device Architecture Files/QLAL4S3B.xml"
	CSVLOCDIR="./EOS-S3/Configuration Bitstream Files"
else
	echo "Error: Unsupported device type: $DEVICE"
	usage
	exit 1
fi

echo "FPGA device: $DEV"
echo "DEVICEXML: $DEVICEXML"
echo "CSVLOCDIR: $CSVLOCDIR"

SCRIPT=./quicklogic_fasm/convert_csv_to_db.py
CSVLOC=${CSVLOCDIR%/}

mkdir -p $OUTDIR
rm -rf $OUTDIR/*

if [ "$DEVICE" == "pp3" ]; then
	# PP3
	python3 $SCRIPT "$CSVLOC/DeviceMacroCoord_$DEV.csv" "$OUTDIR/macro.db" \
	   --cdl "$CSVLOC/QL725A_cdl.cmd" \
	   --include \
	       "$CSVLOC/macroTable_$DEV.csv" \
	       "$CSVLOC/macro_clkTable_$DEV.csv" \
	       "$CSVLOC/macro_gclkTable_$DEV.csv" \
	       "$CSVLOC/macro_interfaceTable_$DEV.csv" \
	   --macro-names \
	       macro \
	       macro_clk \
	       macro_gclk \
	       macro_interface \
	   --techfile "$DEVICEXML" \
	   --routing-bits-outfile "$OUTDIR/macro-routing.db"

	python3 $SCRIPT "$CSVLOC/ColClk_$DEV.csv" "$OUTDIR/colclk.db" --cdl "$CSVLOC/QL725A_cdl.cmd"
	python3 $SCRIPT "$CSVLOC/TestMacro_$DEV.csv" "$OUTDIR/testmacro.db" --cdl "$CSVLOC/QL725A_cdl.cmd"
else
	# EOS-S3
	python3 $SCRIPT "$CSVLOC/DeviceMacroCoord_$DEV.csv" "$OUTDIR/macro.db" \
	   --cdl "$CSVLOC/QL732B_cdl.cmd" \
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

	python3 $SCRIPT "$CSVLOC/ColClk_$DEV.csv" "$OUTDIR/colclk.db" --cdl "$CSVLOC/QL732B_cdl.cmd"
	python3 $SCRIPT "$CSVLOC/TestMacro_$DEV.csv" "$OUTDIR/testmacro.db" --cdl "$CSVLOC/QL732B_cdl.cmd"
fi

