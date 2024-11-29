#!/bin/bash

PARAMETERS=(
#   site        mod         pdf         skip
    "BMB_1       anat        anat"
    "BMB_1       rest        rest"
    "BNU_1       anat        anat"
    "BNU_1       dti         dti"
    "BNU_1       rest        rest"
    "BNU_2       anat1       anat1"
    "BNU_2       anat2       anat2"
    "BNU_2       rest1       rest1"
    "BNU_2       rest2       rest2"
    "BNU_3       anat        anat"
    "BNU_3       dti         dti"
    "BNU_3       rest        rest"
    "IPCAS_5     anat        all         0 1 2 3"
    "IPCAS_5     rest        all         0 1 3 4 5"
    "NKI_TRT     dti         dti"
    "NKI_TRT     rest_645    rest_645"
    "NKI_TRT     rest_1400   rest_1400"
    "NKI_TRT     rest_2500   rest_2500"
    "NYU_2       anat        anat"
    "NYU_2       rest        rest"
    "UM          anat        all         0 1"
    "UM          rest        all         2 3"
    "Utah_1      anat        anat"
    "Utah_1      rest        rest"
    "Utah_2      anat        anat"
    "Utah_2      rest        rest"
    "Utah_2      fieldmap    fieldmap"
    "XHCUMS      anat        all         0 1 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24"
    "XHCUMS      dti         all         0 1 2 3 4 5 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24"
    "XHCUMS      rest        all         0 1 2 3 4 5 6 7 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24"
)

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
            --inp pdf/CoRR/${site}/${inp}.pdf \
            --out p2b/CoRR/${site}/${out}.json \
            --nii nii/CoRR/${site}/${out}.nii
    else
        # skip pages
        p2b \
            --inp pdf/CoRR/${site}/${inp}.pdf \
            --out p2b/CoRR/${site}/${out}.json \
            --nii nii/CoRR/${site}/${out}.nii \
            --skip-pages ${arr[@]}
    fi

done
