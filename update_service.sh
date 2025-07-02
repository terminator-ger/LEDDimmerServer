#!/bin/bash


#!/bin/bash
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

systemctl stop LEDDimmerServer.service
systemctl disable LEDDimmerServer.service  
rm /etc/systemd/system/LEDDimmerServer.service
cp LEDDimmerServer.service /etc/systemd/system/LEDDimmerServer.service
pigpiod
systemctl enable LEDDimmerServer.service
systemctl start LEDDimmerServer.service
