#!/bin/bash

set -e
# iamge_name=$(cd `dirname $0` && pwd)
# echo $image_name
source_path=$(which $0)

dir_name=$(dirname $source_path)



current_branch=$(git branch --show-current)

if [[  $(git diff origin/test HEAD^ $dir_name/*.py) ]]; then
    $dir_name/build.sh
else
    echo "Nothing to update in $(basename $dir_name)"
fi

exit