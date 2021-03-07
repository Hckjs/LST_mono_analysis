#!/usr/bin/bash

# Shell-Script to process data with stage1-tool to DL1-level and merge them afterwards.

set -euxo pipefail

runs="2924"
indir="/home/jonas/aktuell/workb/dvr_test/data/crab/R0"
outdir="/home/jonas/aktuell/workb/dvr_test/data/crab/DL1/lpws/neu"
outdirm="/home/jonas/aktuell/workb/dvr_test/data/crab/DL1/lpws/neu"
config="/home/jonas/pythonsoft/LST_mono_analysis/config/stage1_config.json"

for run in $runs; do
    for filename in $indir/LST-1.1.Run0$run.*.fits.fz; do
        subrun=`basename $filename | cut -d\. -f4`
        echo "Processing run $run subrun $subrun"
        ctapipe-stage1 \
            --input $filename \
            --config $config \
            --output $outdir/dl1_LST-1.Run0$run.$subrun.h5 \
            --progress
    done
done

for run in $runs; do
    echo "Merging run $run"
    ctapipe-merge \
        --input-dir $outdir \
        --output $outdirm/dl1_LST-1.Run0$run.h5 \
        --pattern dl1_LST-1.Run0$run.*.h5 \
        --overwrite \
        --progress
done