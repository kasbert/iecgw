# iecgw
Gateway to Commodore IEC world

 * No fastloaders
 * Unreliable
 * Limited support for 1541 dos functions
 * Simple pi1541 hardware
 * OragePi Zero with armbian. Might work with others, too
 * No Raspberry Pi Zero. Needs multicore.
 * Realtime-ish setup in user space, with a dedicated cpu
 * Full linux networking and services
 * Easyish python server code

TODO
 * Add leds
 * Add 1541/sd2iec dos commands
 * Host mode

IEC code copied from SD2IEC https://www.sd2iec.de/
Hardware is like Pi1541 https://cbm-pi1541.firebaseapp.com/
Some ideas from uno2iec https://github.com/Larswad/uno2iec
Python d64 code frpm ... svn ...


cd src
make
sudo ./iecgw

pip3 install ... cbm f64