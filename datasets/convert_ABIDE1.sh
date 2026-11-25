#!/bin/bash
# Convert the ABIDE1 printouts. Run from the `datasets` directory.

PARAMETERS=(
#   site       out                pdf        [protocol index, see `p2b list`]
    "Caltech    anat               anat"
    "Caltech    rest               rest"
    "CMU_a      rest               rest       0"
    "CMU_b      anat               anat"
    "CMU_b      rest               rest       1"
    # "KKI        anat               anat"
    # "KKI        rest               rest"
    # "Leuven_1   anat               anat"
    # "Leuven_1   rest               rest"
    # "Leuven_2   anat               anat"
    # "Leuven_2   rest               rest"
    "MaxMun_a   anat               anat"
    "MaxMun_a   rest               rest       0"
    "MaxMun_b   anat               anat"
    "MaxMun_b   rest               rest       1"
    "MaxMun_c   anat               anat"
    "MaxMun_c   rest               rest       2"
    "MaxMun_d   anat               anat"
    "MaxMun_d   rest               rest       3"
    "NYU        anat               anat"
    "NYU        rest               rest"
    "OHSU       anat               anat"
    "OHSU       rest               rest"
    "Olin       anat               anat"
    "Olin       rest               rest"
    "Pitt       anat               anat"
    "Pitt       rest               rest"
    # "SBL        anat               anat"
    # "SBL        rest               rest"
    # "SDSU       anat               anat"
    # "SDSU       rest               rest"
    # "Stanford   anat               anat"
    # "Stanford   rest               rest"
    # "Trinity    anat               anat"
    # "Trinity    rest               rest"
    "UCLA_1     anat               anat       0"
    "UCLA_1     anat_hires         anat       1"
    "UCLA_1     rest               rest"
    "UCLA_2     anat               anat       0"
    "UCLA_2     anat_hires         anat       1"
    "UCLA_2     rest               rest"
    # "UM_1       anat               anat"
    # "UM_1       rest               rest"
    # "UM_2       anat               anat"
    # "UM_2       rest               rest"
    "USM        anat               anat"
    "USM        rest               rest"
    "Yale       anat               anat       1"
    "Yale       rest               rest"
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
        --inp "pdf/ABIDE1/${site}/${inp}.pdf" \
        --out "p2b/ABIDE1/${site}/${out}.json" \
        --nii "nii/ABIDE1/${site}/${out}.nii" \
        "${opts[@]}"

done
