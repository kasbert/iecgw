
#ifndef DEBUG_H
#define DEBUG_H
void debugPrint(const char *msg, const char *p, size_t size);
char *state2str(int bus_state);
char *dstate2str(int device_state);
char *atncmd2str(int cmd);
#endif