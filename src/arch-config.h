
#ifndef ARCH_CONFIG_H
#define ARCH_CONFIG_H

#include <wiringPi.h>
#undef TRUE
#undef FALSE
#include <inttypes.h>
#include <unistd.h>
#include <time.h>
#include <sys/time.h>

#define CONFIG_COMMAND_BUFFER_SIZE 256
#define CONFIG_ERROR_BUFFER_SIZE 256
#define CONFIG_BUFFER_COUNT 20
#define ROM_NAME_LENGTH 16
#define CONFIG_MAX_PARTITIONS 1

#undef IEC_INPUTS_INVERTED
#define CONFIG_UART_DEBUG 1

#define VERSION "0.1"
#define LONGVERSION "IECGW 0.1"

typedef uint8_t iec_bus_t;

extern uint8_t command_buffer[CONFIG_COMMAND_BUFFER_SIZE + 2];
extern uint8_t command_length;

void process_iecgw_msg(uint8_t device_address, uint8_t cmd, uint8_t secondary, uint8_t *data, size_t len);

void device_hw_address_init();
// uint8_t device_hw_address();
uint8_t is_hw_address(uint8_t addr);
void parse_doscommand(void);
void file_open(uint8_t secondary);
void file_close(uint8_t secondary);
uint8_t iecgw_loop();

#define system_sleep(x) \
    if (iecgw_loop()) break;

// GPIO

#define IEC_PIN_ATN 0
#define IEC_PIN_DATA 1
#define IEC_PIN_CLOCK 2
#define IEC_PIN_SRQ 3

#define _BV(x) (1 << (x))
#define IEC_BIT_ATN _BV(IEC_PIN_ATN)
#define IEC_BIT_DATA _BV(IEC_PIN_DATA)
#define IEC_BIT_CLOCK _BV(IEC_PIN_CLOCK)
#define IEC_BIT_SRQ _BV(IEC_PIN_SRQ)

#define IEC_ATN get_atn()
#define IEC_DATA get_data()
#define IEC_CLOCK get_clock()
#define IEC_INPUT iec_input()

extern uint8_t m_atnPin;
extern uint8_t m_dataPin;
extern uint8_t m_clockPin;
extern uint8_t m_srqInPin;
extern uint8_t m_resetPin;

static inline uint8_t readPIN(uint8_t pinNumber)
{
    return digitalRead(pinNumber);
}
static inline uint8_t get_atn()
{
    return readPIN(m_atnPin);
}
static inline uint8_t get_data()
{
    return readPIN(m_dataPin);
}
static inline uint8_t get_clock()
{
    return readPIN(m_clockPin);
}
static inline void writePIN(uint8_t pinNumber, uint8_t state)
{
    if (state)
    {
        pinMode(pinNumber, INPUT);
        //pullUpDnControl(pinNumber, PUD_UP);
        // Pulled up
    }
    else
    {
        // Pull down
        pinMode(pinNumber, OUTPUT);
        digitalWrite(pinNumber, 0);
    }
}
static inline void set_atn(uint8_t state)
{
    writePIN(m_atnPin, state);
}
static inline void set_data(uint8_t state)
{
    writePIN(m_dataPin, state);
}
static inline void set_clock(uint8_t state)
{
    writePIN(m_clockPin, state);
}
static inline uint8_t iec_input()
{
    uint8_t ret = ((IEC_ATN ? IEC_BIT_ATN : 0) | (IEC_DATA ? IEC_BIT_DATA : 0) | (IEC_CLOCK ? IEC_BIT_CLOCK : 0));
    return ret;
}

#define iec_interrupts_init()
//#define set_atn_irq(x)
#define IEC_ATN_HANDLER void iec_atn_handler(void)
void iec_atn_handler(void);

static inline void set_atn_irq(uint8_t state) {
  if (state) {
      // Does not work properly
      //wiringPiISR (m_atnPin, INT_EDGE_BOTH,  iec_atn_handler);
  } else {
      //wiringPiISR (m_atnPin, INT_EDGE_BOTH,  0);
  }
}

// Timing

static inline uint64_t timestamp_us()
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    return (uint64_t)ts.tv_sec * (uint64_t)1000000 + (uint64_t)(ts.tv_nsec / 1000);
    /*
    struct timeval tv;
    gettimeofday(&tv, 0);
    return tv.tv_sec * (uint64_t)1000000 + tv.tv_usec;
    */
}
#define start_timeout(us) uint64_t timeout_us = timestamp_us() + (us);
#define has_timed_out() (timestamp_us() > timeout_us)

static inline void delay_us(uint32_t us)
{
    start_timeout(us);
    while (!has_timed_out())
        ;
}

#define delay_ms(x) usleep((x)*1000)

// Compatibility stuff

#define PROGMEM
#define pgm_read_byte(x) (((uint8_t *)x)[0])
#define map_drive(drv) (0)

#define ATOMIC_RESTORESTATE
#define ATOMIC_BLOCK(x)

// Needed in buffers.h
typedef uint8_t dh_t;
typedef uint8_t date_t;
typedef uint8_t d64fh_t;
typedef uint8_t FIL;
typedef uint8_t eefs_fh_t;

extern uint16_t datacrc;
#define display_found 0
extern uint8_t file_extension_mode;
extern uint8_t rom_filename[ROM_NAME_LENGTH + 1];

#define PARALLEL_DIR_IN
#define PARALLEL_DIR_OUT
#define parallel_set_dir(x) \
    do                      \
    {                       \
    } while (0)
#define parallel_send_handshake()
#define parallel_rxflag 0
static inline void parallel_clear_rxflag(void)
{
}
uint8_t jiffy_receive(iec_bus_t *busstate);
uint8_t jiffy_send(uint8_t value, uint8_t eoi, uint8_t loadflags);
int16_t dolphin_getc(void);
uint8_t dolphin_putc(uint8_t data, uint8_t with_eoi);

#define directbuffer_refill ((void*)1)

static inline uint8_t d64_bam_commit(void) { return 0; }
inline void change_disk(void) {}


#define key_pressed(x) 0
#define reset_key(x)

#define display_service() \
    do                    \
    {                     \
    } while (0)
#define display_send_cmd(cmd, len, buf) \
    do                                  \
    {                                   \
    } while (0)
#define display_send_cmd_byte(cmd, v) \
    do                                \
    {                                 \
    } while (0)
#define display_doscommand(len, buf) display_send_cmd(DISPLAY_DOSCOMMAND, len, buf)
#define display_errorchannel(len, buf) display_send_cmd(DISPLAY_ERRORCHANNEL, len, buf)

#endif