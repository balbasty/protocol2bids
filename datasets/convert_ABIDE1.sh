#!/bin/bash

PARAMETERS=(
#   site        mod         pdf         skip
    "Caltech    anat        anat"
    "Caltech    rest        rest"
    "CMU_a      rest        rest        2 3 4"
    "CMU_b      anat        anat"
    # "CMU_b      rest        rest        0 1 4"
    # "KKI        anat        anat"
    # "KKI        rest        rest"
    # "Leuven_1   anat        anat"
    # "Leuven_1   rest        rest"
    # "Leuven_2   anat        anat"
    # "Leuven_2   rest        rest"
    "MaxMun_a   anat        anat"
    "MaxMun_a   rest        rest        1 2 3 4 5 6 7"
    "MaxMun_b   anat        anat"
    "MaxMun_b   rest        rest        0 1 3 4 5 6 7"
    "MaxMun_c   anat        anat"
    "MaxMun_c   rest        rest        0 1 2 3 5 6 7"
    "MaxMun_d   anat        anat"
    "MaxMun_d   rest        rest        0 1 2 3 4 5 7"
    "NYU        anat        anat"
    "NYU        rest        rest"
    "OHSU       anat        anat"
    "OHSU       rest        rest"
    "Olin       anat        anat"
    "Olin       rest        rest"
    "Pitt       anat        anat"
    "Pitt       rest        rest"
    # "SBL        anat        anat"
    # "SBL        rest        rest"
    # "SDSU       anat        anat"
    # "SDSU       rest        rest"
    # "Stanford   anat        anat"
    # "Stanford   rest        rest"
    # "Trinity    anat        anat"
    # "Trinity    rest        rest"
    "UCLA_1     anat        anat        1"
    "UCLA_1     anat_hires  anat        0"
    "UCLA_1     rest        rest"
    "UCLA_2     anat        anat        1"
    "UCLA_2     anat_hires  anat        0"
    "UCLA_2     rest        rest"
    # "UM_1       anat        anat"
    # "UM_1       rest        rest"
    # "UM_2       anat        anat"
    # "UM_2       rest        rest"
    "USM        anat        anat"
    "USM        rest        rest"
    "Yale       anat        anat        0 1"
    "Yale       rest        rest"
)

# PARAMETERS=(
#     "Caltech    anat        anat"
# #     # "CMU_b      rest        rest        0 1 4"
# #     # "MaxMun_d   rest        rest        0 1 2 3 4 5 7"
# #     # "Olin       anat        anat"
# #     # "UCLA_1     anat        anat        1"
# #     # "UCLA_1     rest        rest"
# #     "Yale       rest        rest"
# )

for ((i = 0; i < ${#PARAMETERS[@]}; i++)); do

    prm="${PARAMETERS[$i]}"

    # split parameter row and assign to `arr`
    IFS=" " read -r -a arr <<< "${prm}"

    # read each parameter
    site="${arr[0]}"; arr=("${arr[@]:1}")
    out="${arr[0]}";  arr=("${arr[@]:1}")
    inp="${arr[0]}";  arr=("${arr[@]:1}")
    # what remains in `arr` are the pages to skip

    echo "${site}: ${inp}.pdf -> ${out}.json"

    if [ ${#arr[@]} -eq 0 ]; then
        # no pages to skip
        p2b \
            --inp pdf/ABIDE1/${site}/${inp}.pdf \
            --out p2b/ABIDE1/${site}/${out}.json \
            --nii nii/ABIDE1/${site}/${out}.nii
    else
        # skip pages
        p2b \
            --inp pdf/ABIDE1/${site}/${inp}.pdf \
            --out p2b/ABIDE1/${site}/${out}.json \
            --nii nii/ABIDE1/${site}/${out}.nii \
            --skip-pages ${arr[@]}
    fi

done
