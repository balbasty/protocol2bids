#!/bin/bash
# Convert the CoRR printouts. Run from the `datasets` directory.

PARAMETERS=(
#   site       out                input      [protocol index | -] [p2b options]
    "BMB_1      anat               anat"
    "BMB_1      rest               rest"
    "BNU_1      anat               anat"
    "BNU_1      dti                dti"
    "BNU_1      rest               rest"
    "BNU_2      anat1              anat1"
    "BNU_2      anat2              anat2"
    "BNU_2      rest1              rest1"
    "BNU_2      rest2              rest2"
    "BNU_3      anat               anat"
    "BNU_3      dti                dti"
    "BNU_3      rest               rest"
    "IPCAS_5    anat               all        3"
    "IPCAS_5    rest               all        1"
    "NKI_TRT    dti                dti"
    "NKI_TRT    rest_645           rest_645"
    "NKI_TRT    rest_1400          rest_1400"
    "NKI_TRT    rest_2500          rest_2500"
    "NYU_2      anat               anat"
    "NYU_2      rest               rest"
    "UM         anat               all        1"
    "UM         rest               all        0"
    "Utah_1     anat               anat"
    "Utah_1     rest               rest"
    "Utah_2     anat               anat"
    "Utah_2     rest               rest"
    "Utah_2     fieldmap           fieldmap"
    "XHCUMS     anat               all        1"
    "XHCUMS     dti                all        3"
    "XHCUMS     rest               all        4"
    "IACAS      anat               anat"
    "IACAS      rest               rest"
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
        --inp "pdf/CoRR/${site}/${inp}" \
        --out "p2b/CoRR/${site}/${out}.json" \
        --nii "nii/CoRR/${site}/${out}.nii" \
        "${opts[@]}"

done
