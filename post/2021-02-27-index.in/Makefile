GENERATED = \
	    examplerepo.dot \
	    examplerepo \
	    index.md

%.md: %.in.md
	mdf -f include -f gv -o $@ $<

%: %.yml
	git synth -r $@ $<

%.dot: %
	git -C $< dot -m -g branch --rankdir=RL > $@ || { rm -f $@; exit 1; }

all: $(GENERATED)

index.md: index.in.md examplerepo.dot

clean:
	rm -rf $(GENERATED) gen-*
