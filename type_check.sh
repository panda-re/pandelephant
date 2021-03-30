#! /bin/bash

set -u
cd $(dirname "$0")

# ANSI escape
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NORMAL='\033[0m'

# Add mypy flags/settings here
mypy_cmd=(
    mypy
    --ignore-missing-imports
    --follow-imports skip
    --warn-unreachable
)

# Collect *.py files
py_src_files=()
while IFS= read -r line; do
    py_src_files+=("$line")
done < <(find $(dirname "$0") -type f -name "*.py")

# Typecheck *.py files
echo -e "\n${YELLOW}Running type checks...${NORMAL}\n"
for file_path in "${py_src_files[@]}"
do
    if [[ "$file_path" == *_pb2.py ]]; then
        continue
    fi

    eval "${mypy_cmd[@]} $file_path"
    ret_code=$?
    if [ "$ret_code" -eq 0 ]; then
        echo -e "${GREEN}TYPING OK: $(basename $file_path)${NORMAL}"
    else
        echo -e "${RED}TYPE CHECK FAILED: $(basename $file_path)${NORMAL}"
    fi
done