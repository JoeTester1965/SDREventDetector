#!/bin/bash

VIRTUAL_ENV_DIR=$PWD/venv
CSV_FILE=SDREventDetector.csv

#Use a python virtual env if needed
if [ -d $VIRTUAL_ENV_DIR ]; then
        source $VIRTUAL_ENV_DIR/bin/activate
else
    echo "No local python virtual env at $VIRTUAL_ENV_DIR , see README.md on how to create"
    exit
fi

python3 ./csv_viewer.py $CSV_FILE 0.0

if [[ -z $1 ]]
then
	dir=./output/$(date +%d-%m-%Y-%H-%M)
else
	dir=$1/$(date +%d-%m-%Y-%H-%M)
fi

cp -f events-by-frequency.jpg $dir-events-by-frequency.jpg
cp -f events-by-timeofday.jpg $dir-events-by-timeofday.jpg

deactivate

exit