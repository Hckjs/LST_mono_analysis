#!/usr/bin/bash

input=""
output=""
indir=""

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
