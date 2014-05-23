#!/bin/bash
cd /home/kael/Documents/code/deluge-minister/minister
mkdir temp
export PYTHONPATH=./temp
/usr/bin/python setup.py build develop --install-dir ./temp
cp ./temp/Minister.egg-link /home/kael/.config/deluge/plugins
rm -fr ./temp
