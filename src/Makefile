
all:
	gcc -g -Wall -o iecgw iec.c utils.c buffers.c errormsg.c debug.c compat.c iecgw.c main.c gpio_lib.c

single:
	gcc -DSINGLE_PROCESS -g -Wall -o iecgw iec.c utils.c buffers.c errormsg.c debug.c compat.c iecgw.c main.c gpio_lib.c

wiring:
	gcc -DWIRINGPI -g -Wall -o iecgw iec.c utils.c buffers.c errormsg.c debug.c compat.c iecgw.c main.c -lwiringPi

clean:
	rm -f iecgw
