
#ifndef ARCH_CONFIG_H
#define ARCH_CONFIG_H

#ifdef WIRINGPI
#include <wiringPi.h>
#undef TRUE
#undef FALSE
#else
#include "gpio_lib.h"
#endif
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

void device_hw_address_init();
// uint8_t device_hw_address();
uint8_t is_hw_address(uint8_t addr);
void parse_doscommand(void);
void file_open(uint8_t secondary);
void file_close(uint8_t secondary);
uint8_t check_input();

#define system_sleep(x) \
    if (check_input()) break;

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

#ifdef WIRINGPI
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

static inline void set_data1()
{
    // with pull up
    pinMode(m_dataPin, INPUT);
}

static inline void set_data0()
{
    pinMode(m_dataPin, OUTPUT);
    digitalWrite(m_dataPin, 0);
}

static inline void set_clock1()
{
    // with pull up
    pinMode(m_clockPin, INPUT);
}

static inline void set_clock0()
{
    pinMode(m_clockPin, OUTPUT);
    digitalWrite(m_clockPin, 0);
}

static inline void set_atn1()
{
    // with pull up
    pinMode(m_atnPin, INPUT);
}

static inline void set_atn0()
{
    pinMode(m_atnPin, OUTPUT);
    digitalWrite(m_atnPin, 0);
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
#else
extern uint8_t m_atnPin;
extern uint8_t m_dataPin;
extern uint8_t m_clockPin;
extern uint8_t m_srqInPin;
extern uint8_t m_resetPin;

extern struct gpio_reg gpio_reg_atn;
extern struct gpio_reg gpio_reg_data;
extern struct gpio_reg gpio_reg_clock;

unsigned int micros (void);

static inline uint8_t get_atn()
{
    return gpio_reg_input(&gpio_reg_atn);
}
static inline uint8_t get_data()
{
    return gpio_reg_input(&gpio_reg_data);
}
static inline uint8_t get_clock()
{
    return gpio_reg_input(&gpio_reg_clock);
}

static inline void set_data1()
{
    // with pull up
    //gpio_reg_set_cfg(&gpio_reg_data, SUNXI_GPIO_INPUT);
    gpio_reg_set_input(&gpio_reg_data);
}

static inline void set_data0()
{
    //gpio_reg_set_cfg(&gpio_reg_data, SUNXI_GPIO_OUTPUT);
    gpio_reg_set_output(&gpio_reg_data);
    gpio_reg_output0(&gpio_reg_data);
}

static inline void set_clock1()
{
    // with pull up
    //gpio_reg_set_cfg(&gpio_reg_clock, SUNXI_GPIO_INPUT);
    gpio_reg_set_input(&gpio_reg_clock);
}

static inline void set_clock0()
{
    //gpio_reg_set_cfg(&gpio_reg_clock, SUNXI_GPIO_OUTPUT);
    gpio_reg_set_output(&gpio_reg_clock);
    gpio_reg_output0(&gpio_reg_clock);
}

static inline void set_atn1()
{
    // with pull up
    gpio_reg_set_cfg(&gpio_reg_atn, SUNXI_GPIO_INPUT);
}

static inline void set_atn0()
{
    gpio_reg_set_cfg(&gpio_reg_atn, SUNXI_GPIO_OUTPUT);
    gpio_reg_output0(&gpio_reg_atn);
}
//
static inline uint8_t readPIN(uint8_t pinNumber)
{
    return sunxi_gpio_input(pinNumber);
}

/*
static inline void writePIN(uint8_t pinNumber, uint8_t state)
{
    if (state)
    {
        // Pulled up
        sunxi_gpio_set_cfgpin(pinNumber, SUNXI_GPIO_INPUT);
    }
    else
    {
        // Pull down
        sunxi_gpio_set_cfgpin(pinNumber, SUNXI_GPIO_OUTPUT);
        sunxi_gpio_output(pinNumber, LOW);
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
*/

#endif

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

// 24Mhz timer, counting down
#define UNITS_PER_us(t) (t*24)
#define UNITS_PER_100ns(t) ((t*24)/10)
extern volatile uint32_t *timer_register;
#define timer_count() (*timer_register)

#define start_timeout(us) uint32_t timeout_us = timer_count() - UNITS_PER_us(us);
#define has_timed_out() ((uint32_t)(timer_count() - timeout_us) >= 0x80000000)

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
