#!/bin/bash

retcode=0

python3 -m pip install -U LEDDimmerServer

while true; do  
    source /home/led/LEDDimmerServer/ledvenv/bin/activate

    if [ "$retcode" -eq 42 ]; then
        # update
        python3 -m pip install -U LEDDimmerServer
    fi

    # exec service
    python3 -m LEDDimmerServer
    retcode=$?
done