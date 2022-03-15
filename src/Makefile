
SRC=iec.c utils.c buffers.c errormsg.c debug.c compat.c iecgw.c main.c gpio_lib.c llfl-common.c llfl-jiffydos.c

all:
	gcc -O -g -Wall -o iecgw $(SRC)

single:
	gcc -DSINGLE_PROCESS -g -O -Wall -o iecgw $(SRC)

wiring:
	gcc -DWIRINGPI -g -O -Wall -o iecgw $(SRC) -lwiringPi

clean:
	rm -f iecgw
