#!/bin/bash

retcode=0
while :
do
    if [$retcode -eq 42]; then
        #update
        /usr/bin/yes | /bin/python3 -m pip -U LEDDimmerServer
    fi
    #exec service
    LEDDimmerServer
    retcode=$?
done
