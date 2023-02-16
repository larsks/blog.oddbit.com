all: example

example: example.o must.o
	$(CC) -o $@ $^

clean:
	rm -f example example.o must.o
