SRCS = $(wildcard sendpacket-*.c)
OBJS = $(SRCS:.c=.o)
BINS = $(SRCS:.c=)

%: %.o
	$(CC) -o $@ $<

all: $(BINS)

clean:
	rm -f $(BINS) $(OBJS)
