
#ifndef DEBUG_H
#define DEBUG_H

void debug_state();
void debug_atn_command(char *message, uint8_t cmd1);

void debug_print_buffer(const char *msg, unsigned const char *p, size_t size);
char *state2str(int bus_state);
char *dstate2str(int device_state);
char *atncmd2str(int cmd);
#endif