#!/bin/bash
# Convert the ABIDE2 printouts. Run from the `datasets` directory.

PARAMETERS=(
    # Philips sites: the ExamCard text exports (*.txt) are richer than
    # the scan tables. SDSU_1: the scan sheets print "TE: Min Full" and
    # no TR/field strength, which are filled from the site scan table.
    # NYU dwi: user sequence whose flip angle (60 deg) is only given in
    # the scan table.
#   site       out                input      [protocol index | -] [p2b options]
    "BNI_1      T1w                T1w.txt"
    "BNI_1      bold               bold.txt"
    "BNI_1      dwi                dwi.txt"
    "EMC_1      T1w                T1w"
    "EMC_1      bold               bold"
    "ETH_1      T1w                T1w.txt"
    "ETH_1      bold               bold.txt"
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
    "KUL_3      T1w                T1w.txt"
    "KUL_3      bold               bold.txt"
    "NYU_1      T1w                T1w"
    "NYU_1      bold               bold"
    "NYU_1      dwi                dwi        -  --fill-from pdf/ABIDE2/NYU_1/scantable.pdf --fill-select 2"
    "NYU_1      fieldmap           fieldmap"
    "NYU_2      T1w                T1w"
    "NYU_2      bold               bold"
    "NYU_2      dwi                dwi        -  --fill-from pdf/ABIDE2/NYU_2/scantable.pdf --fill-select 2"
    "NYU_2      fieldmap           fieldmap"
    "OHSU_1     T1w                T1w"
    "OHSU_1     bold               bold       0"
    "ONRC_2     T1w                T1w"
    "ONRC_2     bold               bold"
    "SDSU_1     T1w                T1w        -  --fill-from pdf/ABIDE2/SDSU_1/scantable.pdf --fill-select 0"
    "SDSU_1     bold               bold       -  --fill-from pdf/ABIDE2/SDSU_1/scantable.pdf --fill-select 1"
    "TCD_1      T1w                T1w.txt"
    "TCD_1      bold               bold.txt"
    "TCD_1      dwi                dwi.txt"
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

    # split parameter row:
    #   site, output name, input (pdf by default), [protocol index or "-"],
    #   [extra p2b options]
    IFS=" " read -r -a arr <<< "${PARAMETERS[$i]}"
    site="${arr[0]}"
    out="${arr[1]}"
    inp="${arr[2]}"
    [[ "${inp}" == *.* ]] || inp="${inp}.pdf"
    opts=()
    if [ ${#arr[@]} -gt 3 ] && [ "${arr[3]}" != "-" ]; then
        opts=(--select "${arr[3]}")
    fi
    if [ ${#arr[@]} -gt 4 ]; then
        opts+=("${arr[@]:4}")
    fi

    echo "${site}: ${inp} -> ${out}.json"
    p2b \
        --inp "pdf/ABIDE2/${site}/${inp}" \
        --out "p2b/ABIDE2/${site}/${out}.json" \
        --nii "nii/ABIDE2/${site}/${out}.nii" \
        "${opts[@]}"

done
