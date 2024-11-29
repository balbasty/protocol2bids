#!/bin/bash

CORR_BASES=(
    beijing_eoec_anat
    beijing_eoec_rest
    beijing_eoec_DTI
    beijing_he_anat
    beijing_he_rest
    beijing_he_DTI
    beijing_liu_anat1
    beijing_liu_anat2
    beijing_liu_rest1
    beijing_liu_rest2
    berlin_anat
    berlin_rest
)

for base in ${CORR_BASES[@]}; do

    p2b \
        --inp examples/pdf/corr/siemens/${base}.pdf \
        --out examples/json/corr/siemens/${base}.json \
        --nii examples/nii/corr/siemens/${base}.nii

done

p2b \
    --inp examples/pdf/corr/siemens/ipcas_wei_all.pdf \
    --out examples/json/corr/siemens/ipcas_wei_anat.json \
    --nii examples/nii/corr/siemens/ipcas_wei_anat.nii \
    --skip-pages 0 1 2 3

p2b \
    --inp examples/pdf/corr/siemens/ipcas_wei_all.pdf \
    --out examples/json/corr/siemens/ipcas_wei_rest.json \
    --nii examples/nii/corr/siemens/ipcas_wei_rest.nii \
    --skip-pages 0 1 3 4 5
