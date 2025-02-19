#!/bin/bash
nohup pkill -f zmqpubsink.py  &> /dev/null
nohup pkill -f SDREventDetector.py  &> /dev/null
nohup pkill -9 -f zmqpubsink.py  &> /dev/null
nohup pkill -9 -f SDREventDetector.py  &> /dev/null