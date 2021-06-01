
all:
	gcc -g -Wall -o iecgw iec.c buffers.c errormsg.c utils.c  debug.c compat.c iecgw.c main.c -lwiringPi

single:
	gcc -DSINGLE_PROCESS -g -Wall -o iecgw iec.c buffers.c errormsg.c utils.c  debug.c compat.c iecgw.c main.c -lwiringPi

clean:
	rm -f iecgw
