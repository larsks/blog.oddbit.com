UMLS = $(wildcard *.plantuml)
SVGS = $(UMLS:.plantuml=.svg)

%.svg: %.plantuml
	plantuml -tsvg $<

all: $(SVGS)

clean:
	rm -f $(SVGS)
