#!/bin/bash

directory_path="../"

fswatch -r -e ".*" -i "\\.log$" "$directory_path" |
    while read filename
    do
        echo "File '$filename' was modified."
    done