#!/usr/bin/bash

# Shell-Script to process data with stage1-tool to DL1-level and merge them afterwards.

set -euxo pipefail

indir=$1
output=$2
config=$3

outdir=`dirname $output`
run=`basename $output | cut -d\. -f2`

for filename in $indir/LST-1.1.$run.*.fits.fz; do
	subrun=`basename $filename | cut -d\. -f4`
	echo "Processing run $run subrun $subrun"
	ctapipe-stage1 \
    --input $filename \
    --config $config \
    --output $outdir/dl1_LST-1.$run.$subrun.h5 \
	--progress
done

echo "Merging run $run"
ctapipe-merge \
--input-dir $outdir \
--output $output \
--pattern dl1_LST-1.$run.*.h5 \
--overwrite \
--progress
