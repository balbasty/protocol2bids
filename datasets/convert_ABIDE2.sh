#!/bin/bash
# Convert the ABIDE2 printouts. Run from the `datasets` directory.

PARAMETERS=(
#   site       out                pdf        [protocol index, see `p2b list`]
    "BNI_1      T1w                scantable  0"
    "BNI_1      bold               scantable  1"
    # "BNI_1      dwi                scantable  2"  # no DTI column
    "EMC_1      T1w                T1w"
    "EMC_1      bold               bold"
    "ETH_1      T1w                scantable  0"
    "ETH_1      bold               scantable  1"
    "GU_1       T1w                T1w"
    "IP_1       T1w                T1w"
    "IP_1       bold               bold"
    "IP_1       dwi                dwi"
    "IU_1       T1w                T1w"
    "IU_1       bold               bold"
    "KKI_1      acq-rc8chan_T1w    acq-rc8chan_T1w"
    "KKI_1      acq-rc32chan_T1w   acq-rc32chan_T1w"
    "KKI_1      acq-rc8chan_bold   bold"
    "KKI_1      acq-rc32chan_bold  bold"
    "KUL_3      T1w                scantable  0"
    "KUL_3      bold               scantable  1"
    "NYU_1      T1w                T1w"
    "NYU_1      bold               bold"
    "NYU_1      dwi                dwi"
    "NYU_1      fieldmap           fieldmap"
    "NYU_2      T1w                T1w"
    "NYU_2      bold               bold"
    "NYU_2      dwi                dwi"
    "NYU_2      fieldmap           fieldmap"
    "OHSU_1     T1w                T1w"
    "OHSU_1     bold               bold       0"
    "ONRC_2     T1w                T1w"
    "ONRC_2     bold               bold"
    "SDSU_1     T1w                T1w"
    "SDSU_1     bold               bold"
    "TCD_1      T1w                scantable  0"
    "TCD_1      bold               scantable  1"
    "TCD_1      dwi                scantable  2"
    "UCD_1      T1w                T1w"
    "UCD_1      bold               bold"
    "UCLA_1     T1w                T1w"
    # "UCLA_1     acq-hires_T1w      acq-hires_T1w"
    "UCLA_1     bold               bold"
    "UCLA_Long  T1w                T1w"
    # "UCLA_Long  acq-hires_T1w      acq-hires_T1w"
    "UCLA_Long  bold               bold"
    "UPSM_Long  T1w                T1w"
    "UPSM_Long  bold               bold"
    "USM_1      T1w                T1w"
    "USM_1      bold               bold"
)

for ((i = 0; i < ${#PARAMETERS[@]}; i++)); do

    # split parameter row: site, output name, input pdf, [protocol index]
    IFS=" " read -r -a arr <<< "${PARAMETERS[$i]}"
    site="${arr[0]}"
    out="${arr[1]}"
    inp="${arr[2]}"
    opts=()
    if [ ${#arr[@]} -gt 3 ]; then
        opts=(--select "${arr[3]}")
    fi

    echo "${site}: ${inp}.pdf -> ${out}.json"
    p2b \
        --inp "pdf/ABIDE2/${site}/${inp}.pdf" \
        --out "p2b/ABIDE2/${site}/${out}.json" \
        --nii "nii/ABIDE2/${site}/${out}.nii" \
        "${opts[@]}"

done
