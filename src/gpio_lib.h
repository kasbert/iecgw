#ifndef _GPIO_LIB_H_
#define _GPIO_LIB_H_


#define SW_PORTC_IO_BASE 0x01c20800


#define SUNXI_GPIO_A	0
#define SUNXI_GPIO_B	1
#define SUNXI_GPIO_C	2
#define SUNXI_GPIO_D	3
#define SUNXI_GPIO_E	4
#define SUNXI_GPIO_F	5
#define SUNXI_GPIO_G	6
#define SUNXI_GPIO_H	7
#define SUNXI_GPIO_I	8

#define SETUP_OK            0
#define SETUP_DEVMEM_FAIL   1
#define SETUP_MALLOC_FAIL   2
#define SETUP_MMAP_FAIL     3

#define HIGH    1
#define LOW     0

#define INPUT   0
#define OUTPUT  1
#define PER     2

#define DISABLE	0
#define UP	1
#define DOWN	2

#define SUNXI_GPIO_PULL_DISABLE	0
#define SUNXI_GPIO_PULL_UP	1
#define SUNXI_GPIO_PULL_DOWN	2


struct sunxi_gpio {
    unsigned int cfg[4];
    unsigned int dat;
    unsigned int drv[2];
    unsigned int pull[2];
};

/* gpio interrupt control */
struct sunxi_gpio_int {
    unsigned int cfg[3];
    unsigned int ctl;
    unsigned int sta;
    unsigned int deb;
};

struct sunxi_gpio_reg {
    struct sunxi_gpio gpio_bank[9];
    unsigned char res[0xbc];
    struct sunxi_gpio_int gpio_int;
};

#define GPIO_BANK(pin)	((pin) >> 5)
#define GPIO_NUM(pin)	((pin) & 0x1F)

#define GPIO_CFG_INDEX(pin)	(((pin) & 0x1F) >> 3)
#define GPIO_CFG_OFFSET(pin)	((((pin) & 0x1F) & 0x7) << 2)

#define GPIO_PULL_INDEX(pin)	(((pin) & 0x1F) >> 4)
#define GPIO_PULL_OFFSET(pin)	((((pin) & 0x1F) & 0xf) << 1)

/* GPIO bank sizes */
#define SUNXI_GPIO_A_NR		(32)
#define SUNXI_GPIO_B_NR		(32)
#define SUNXI_GPIO_C_NR		(32)
#define SUNXI_GPIO_D_NR		(32)
#define SUNXI_GPIO_E_NR		(32)
#define SUNXI_GPIO_F_NR		(32)
#define SUNXI_GPIO_G_NR		(32)
#define SUNXI_GPIO_H_NR		(32)
#define SUNXI_GPIO_I_NR		(32)

#define SUNXI_GPIO_NEXT(__gpio) ((__gpio##_START)+(__gpio##_NR)+0)

enum sunxi_gpio_number {
    SUNXI_GPIO_A_START = 0,
    SUNXI_GPIO_B_START = SUNXI_GPIO_NEXT(SUNXI_GPIO_A),	//32
    SUNXI_GPIO_C_START = SUNXI_GPIO_NEXT(SUNXI_GPIO_B),	//64
    SUNXI_GPIO_D_START = SUNXI_GPIO_NEXT(SUNXI_GPIO_C),	//96
    SUNXI_GPIO_E_START = SUNXI_GPIO_NEXT(SUNXI_GPIO_D),	//128
    SUNXI_GPIO_F_START = SUNXI_GPIO_NEXT(SUNXI_GPIO_E),	//160
    SUNXI_GPIO_G_START = SUNXI_GPIO_NEXT(SUNXI_GPIO_F),	//192
    SUNXI_GPIO_H_START = SUNXI_GPIO_NEXT(SUNXI_GPIO_G),	//224
    SUNXI_GPIO_I_START = SUNXI_GPIO_NEXT(SUNXI_GPIO_H)	//256
};

/* SUNXI GPIO number definitions */
#define SUNXI_GPA(_nr) (SUNXI_GPIO_A_START + (_nr))
#define SUNXI_GPB(_nr) (SUNXI_GPIO_B_START + (_nr))
#define SUNXI_GPC(_nr) (SUNXI_GPIO_C_START + (_nr))
#define SUNXI_GPD(_nr) (SUNXI_GPIO_D_START + (_nr))
#define SUNXI_GPE(_nr) (SUNXI_GPIO_E_START + (_nr))
#define SUNXI_GPF(_nr) (SUNXI_GPIO_F_START + (_nr))
#define SUNXI_GPG(_nr) (SUNXI_GPIO_G_START + (_nr))
#define SUNXI_GPH(_nr) (SUNXI_GPIO_H_START + (_nr))
#define SUNXI_GPI(_nr) (SUNXI_GPIO_I_START + (_nr))

/* GPIO pin function config */
#define SUNXI_GPIO_INPUT (0)
#define SUNXI_GPIO_OUTPUT (1)
#define SUNXI_GPIO_PER (2)

#define SUNXI_GPA0_ERXD3 (2)
#define SUNXI_GPA0_SPI1_CS0 (3)
#define SUNXI_GPA0_UART2_RTS (4)

#define SUNXI_GPA1_ERXD2 (2)
#define SUNXI_GPA1_SPI1_CLK	(3)
#define SUNXI_GPA1_UART2_CTS	(4)

#define SUNXI_GPA2_ERXD1	(2)
#define SUNXI_GPA2_SPI1_MOSI	(3)
#define SUNXI_GPA2_UART2_TX	(4)

#define SUNXI_GPA10_UART1_TX	(4)
#define SUNXI_GPA11_UART1_RX	(4)

#define SUN4I_GPB22_UART0_TX	(2)
#define SUN4I_GPB23_UART0_RX	(2)

#define SUN5I_GPG3_UART0_TX	(4)
#define SUN5I_GPG4_UART0_RX	(4)

#define SUNXI_GPC2_NCLE	(2)
#define SUNXI_GPC2_SPI0_CLK	(3)

#define SUNXI_GPC6_NRB0	(2)
#define SUNXI_GPC6_SDC2_CMD	(3)

#define SUNXI_GPC7_NRB1	(2)
#define SUNXI_GPC7_SDC2_CLK	(3)

#define SUNXI_GPC8_NDQ0	(2)
#define SUNXI_GPC8_SDC2_D0	(3)

#define SUNXI_GPC9_NDQ1	(2)
#define SUNXI_GPC9_SDC2_D1	(3)

#define SUNXI_GPC10_NDQ2	(2)
#define SUNXI_GPC10_SDC2_D2	(3)

#define SUNXI_GPC11_NDQ3	(2)
#define SUNXI_GPC11_SDC2_D3	(3)

#define SUNXI_GPF2_SDC0_CLK	(2)
#define SUNXI_GPF2_UART0_TX	(4)

#define SUNXI_GPF4_SDC0_D3	(2)
#define SUNXI_GPF4_UART0_RX	(4)

extern int sunxi_gpio_input(unsigned int pin);
extern int sunxi_gpio_init(void);
extern int sunxi_gpio_set_cfgpin(unsigned int pin, unsigned int val);
extern int sunxi_gpio_get_cfgpin(unsigned int pin);
extern int sunxi_gpio_set_pull(unsigned int pin, unsigned int val);
extern int sunxi_gpio_output(unsigned int pin, unsigned int val);
extern void sunxi_gpio_cleanup(void);

extern unsigned int SUNXI_PIO_BASE;

// Fast versions
struct gpio_reg {
    volatile unsigned int *data_ptr;
    unsigned int num;
    unsigned int num_mask1;
    unsigned int num_mask0;
    volatile unsigned int *cfg_ptr;
    unsigned int cfg_offset;
    unsigned int cfg_mask_input;
    unsigned int cfg_mask_output;
    volatile unsigned int *pull_ptr;
    unsigned int pull_offset;
};

extern int gpio_reg_init(struct gpio_reg * reg, unsigned int pin) ;

static inline void gpio_reg_set_input(struct gpio_reg * reg) {
    //*(reg->cfg_ptr) &= ~(0xf << reg->cfg_offset);
    *(reg->cfg_ptr) &= reg->cfg_mask_input;
}
static inline void gpio_reg_set_output(struct gpio_reg * reg) {
    //*(reg->cfg_ptr) |= 1 << reg->cfg_offset;
    *(reg->cfg_ptr) |= reg->cfg_mask_output;
}

static inline void gpio_reg_set_cfg(struct gpio_reg * reg, unsigned int val) {
    unsigned int cfg = *(reg->cfg_ptr);
    cfg &= ~(0xf << reg->cfg_offset);
    cfg |= val << reg->cfg_offset;
    *(reg->cfg_ptr) = cfg;
}

static inline int gpio_reg_get_cfg(struct gpio_reg * reg) {
    unsigned int cfg = *(reg->cfg_ptr);
    cfg >>= reg->cfg_offset;
    return (cfg & 0xf);
}

static inline void gpio_reg_set_pull(struct gpio_reg * reg, unsigned int val) {
    unsigned int pull = *(reg->pull_ptr);
    pull &= ~(0x3 << reg->pull_offset);
    pull |= val << reg->pull_offset;
    *(reg->pull_ptr) = pull;
}

static inline int gpio_reg_input(struct gpio_reg * reg) {
    unsigned int dat = *(reg->data_ptr);
    dat >>= reg->num;
    return (dat & 0x1);
}

static inline void gpio_reg_output(struct gpio_reg * reg, unsigned int val) {
    if(val)
        *(reg->data_ptr) |= 1 << reg->num;
    else
        *(reg->data_ptr) &= ~(1 << reg->num);
}

static inline void gpio_reg_output1(struct gpio_reg * reg) {
    //*(reg->data_ptr) |= 1 << reg->num;
    *(reg->data_ptr) |= reg->num_mask1;
}

static inline void gpio_reg_output0(struct gpio_reg * reg) {
    //*(reg->data_ptr) &= ~(1 << reg->num);
    *(reg->data_ptr) &= reg->num_mask0;
}

#endif
