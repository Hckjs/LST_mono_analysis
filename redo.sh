#!/usr/bin/bash

input="/home/jonas/aktuell/workb/dvr_test/data/crab/DL1/lpws/dl1_LST-1.Run02924.h5"
output="/home/jonas/aktuell/workb/dvr_test/data/crab/DL1/lpws/dl1_dvr_LST-1.Run02924.h5"
indir="/home/jonas/aktuell/workb/dvr_test/data/crab/DL1/lpws"

cp \
	$input \
	$indir/tempfile.h5

python redo_dl0_dl1.py \
	$indir/tempfile.h5

ptrepack \
	$indir/tempfile.h5 \
	$output \
	--keep-source-filters

rm -f $indir/tempfile.h5
