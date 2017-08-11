#!/bin/bash

set -e

while true;
do
    ./coded_digits.py $(date +%H%M) -p "$@"
done
