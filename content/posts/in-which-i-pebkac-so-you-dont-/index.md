---
categories: [tech]
aliases: ["/2019/02/11/in-which-i-pebkac-so-you-dont-/"]
title: "In which I PEBKAC so you don't have to"
date: "2019-02-11"
tags:
- "avr"
- "gcc"
---

Say you have a simple bit of code:

    #include <avr/io.h>
    #include <util/delay.h> 

    #define LED_BUILTIN _BV(PORTB5)

    int main(void) 
    {
        DDRB |= LED_BUILTIN;

        while (1)
        {
            PORTB |= LED_BUILTIN;   // turn on led
            _delay_ms(1000);        // delay 1s

            PORTB &= ~LED_BUILTIN;  // turn off led
            _delay_ms(1000);        // delay 1s
        }                                                
    }

You have a Makefile that compiles that into an object (`.o`) file like this:

    avr-gcc -mmcu=atmega328p -DF_CPU=16000000 -Os -c blink.c

If you were to forget to set the device type when compiling your `.c` file into an object file (`.o`), you would get a warning:

    $ avr-gcc -DF_CPU=16000000 -Os -c blink.c
    In file included from blink.c:1:0:
    /usr/avr/include/avr/io.h:623:6: warning: #warning "device type not defined" [-Wcpp]
     #    warning "device type not defined"
          ^~~~~~~

But if you were to forget to set the device type when linking the final ELF binary, you would not be so lucky:

    $ avr-gcc -o blink.elf blink.o
    <...silence...>

So you would, perhaps, be surprised when you flash this to your device and it doesn't work.  If you take a look at the assembly generated for the above command, it looks like this:

    $ avr-objdump -d blink.elf
    blink.elf:     file format elf32-avr


    Disassembly of section .text:

    00000000 <main>:
       0:   25 9a           sbi     0x04, 5 ; 4
       2:   2d 9a           sbi     0x05, 5 ; 5
       4:   2f e3           ldi     r18, 0x3F       ; 63
       6:   8d e0           ldi     r24, 0x0D       ; 13
       8:   93 e0           ldi     r25, 0x03       ; 3
       a:   21 50           subi    r18, 0x01       ; 1
       c:   80 40           sbci    r24, 0x00       ; 0
       e:   90 40           sbci    r25, 0x00       ; 0
      10:   e1 f7           brne    .-8             ; 0xa <__zero_reg__+0x9>
      12:   00 c0           rjmp    .+0             ; 0x14 <__zero_reg__+0x13>
      14:   00 00           nop
      16:   2d 98           cbi     0x05, 5 ; 5
      18:   2f e3           ldi     r18, 0x3F       ; 63
      1a:   8d e0           ldi     r24, 0x0D       ; 13
      1c:   93 e0           ldi     r25, 0x03       ; 3
      1e:   21 50           subi    r18, 0x01       ; 1
      20:   80 40           sbci    r24, 0x00       ; 0
      22:   90 40           sbci    r25, 0x00       ; 0
      24:   e1 f7           brne    .-8             ; 0x1e <__zero_reg__+0x1d>
      26:   00 c0           rjmp    .+0             ; 0x28 <__zero_reg__+0x27>
      28:   00 00           nop
      2a:   eb cf           rjmp    .-42            ; 0x2 <__zero_reg__+0x1>

If you remember to include the device type:

    $ avr-gcc -mmcu=atmega328p -o blink.elf blink.o

You instead get:

    $ avr-objdump -d blink.elf
    blink.elf:     file format elf32-avr


    Disassembly of section .text:

    00000000 <__vectors>:
       0:	0c 94 34 00 	jmp	0x68	; 0x68 <__ctors_end>
       4:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
       8:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
       c:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      10:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      14:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      18:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      1c:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      20:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      24:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      28:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      2c:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      30:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      34:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      38:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      3c:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      40:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      44:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      48:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      4c:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      50:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      54:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      58:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      5c:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      60:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>
      64:	0c 94 3e 00 	jmp	0x7c	; 0x7c <__bad_interrupt>

    00000068 <__ctors_end>:
      68:	11 24       	eor	r1, r1
      6a:	1f be       	out	0x3f, r1	; 63
      6c:	cf ef       	ldi	r28, 0xFF	; 255
      6e:	d8 e0       	ldi	r29, 0x08	; 8
      70:	de bf       	out	0x3e, r29	; 62
      72:	cd bf       	out	0x3d, r28	; 61
      74:	0e 94 40 00 	call	0x80	; 0x80 <main>
      78:	0c 94 56 00 	jmp	0xac	; 0xac <_exit>

    0000007c <__bad_interrupt>:
      7c:	0c 94 00 00 	jmp	0	; 0x0 <__vectors>

    00000080 <main>:
      80:	25 9a       	sbi	0x04, 5	; 4
      82:	2d 9a       	sbi	0x05, 5	; 5
      84:	2f e3       	ldi	r18, 0x3F	; 63
      86:	8d e0       	ldi	r24, 0x0D	; 13
      88:	93 e0       	ldi	r25, 0x03	; 3
      8a:	21 50       	subi	r18, 0x01	; 1
      8c:	80 40       	sbci	r24, 0x00	; 0
      8e:	90 40       	sbci	r25, 0x00	; 0
      90:	e1 f7       	brne	.-8      	; 0x8a <main+0xa>
      92:	00 c0       	rjmp	.+0      	; 0x94 <main+0x14>
      94:	00 00       	nop
      96:	2d 98       	cbi	0x05, 5	; 5
      98:	2f e3       	ldi	r18, 0x3F	; 63
      9a:	8d e0       	ldi	r24, 0x0D	; 13
      9c:	93 e0       	ldi	r25, 0x03	; 3
      9e:	21 50       	subi	r18, 0x01	; 1
      a0:	80 40       	sbci	r24, 0x00	; 0
      a2:	90 40       	sbci	r25, 0x00	; 0
      a4:	e1 f7       	brne	.-8      	; 0x9e <main+0x1e>
      a6:	00 c0       	rjmp	.+0      	; 0xa8 <main+0x28>
      a8:	00 00       	nop
      aa:	eb cf       	rjmp	.-42     	; 0x82 <main+0x2>

    000000ac <_exit>:
      ac:	f8 94       	cli

    000000ae <__stop_program>:
      ae:	ff cf       	rjmp	.-2      	; 0xae <__stop_program>

You can see that this code includes things like the jump table, without which your code won't run.

The moral of this story is: don't forget to set the device type.
