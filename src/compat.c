
#include <stdint.h>
#include <stdio.h>

#include "arch-config.h"
#include "buffers.h"

uint8_t command_buffer[CONFIG_COMMAND_BUFFER_SIZE + 2];
uint8_t command_length;

volatile uint8_t led_state;
uint8_t globalflags;
uint16_t datacrc;
uint8_t image_as_dir;
uint8_t rom_filename[ROM_NAME_LENGTH + 1];
uint8_t file_extension_mode;

// TODO make configurable
uint8_t m_atnPin = 6;
uint8_t m_dataPin = 0;
uint8_t m_clockPin = 1;
uint8_t m_srqInPin = 2;
uint8_t m_resetPin = 5;
uint8_t m_dirtyLedPin = -1;
uint8_t m_busyLedPin = -1;

void gpio_init()
{
  pinMode(m_atnPin, INPUT);
  pinMode(m_dataPin, INPUT);
  pinMode(m_clockPin, INPUT);
  pinMode(m_srqInPin, INPUT);
  pinMode(m_resetPin, INPUT);

  pullUpDnControl(m_atnPin, PUD_UP);
  pullUpDnControl(m_dataPin, PUD_UP);
  pullUpDnControl(m_clockPin, PUD_UP);
  pullUpDnControl(m_srqInPin, PUD_UP);
  pullUpDnControl(m_resetPin, PUD_UP);

}

void uart_putc(char c)
{
  putchar(c);
}
void uart_putcrlf(void)
{
  putchar('\n');
}
void uart_puthex(uint8_t num)
{
  printf("%02x", num);
}

// TODO add leds
void set_dirty_led(uint8_t state) {}
void set_busy_led(uint8_t state) {}
void update_leds(void)
{
  set_busy_led(active_buffers != 0);
  set_dirty_led(get_dirty_buffer_count() != 0);
}

uint8_t jiffy_receive(iec_bus_t *busstate)
{
  printf("jiffy_receive\n");
  return 0;
}

uint8_t jiffy_send(uint8_t value, uint8_t eoi, uint8_t loadflags)
{
  printf("jiffy_send\n");
  return 0;
}

int16_t dolphin_getc(void)
{
  printf("dolphin_getc\n");
  return 0;
}

uint8_t dolphin_putc(uint8_t data, uint8_t with_eoi)
{
  printf("dolphin_putc\n");
  return 0;
}
