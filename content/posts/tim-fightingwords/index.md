---
categories:
- tech
date: '2025-10-11'
tags:
- things-i-made
title: "Things I Made: Fighting words generator"
---

If you've ever seen the 1960's live-action Batman TV show, you'll know that one of the defining characteristics of the show was its use of comic-book style words overlaying the action scenes, a technique pioneered in comic books by Roy Crane:

> It was Crane who pioneered the use of onomatopoeic sound effects in comics,
> adding "bam," "pow" and "wham" to what had previously been an almost entirely
> visual vocabulary. Crane had fun with this, tossing in an occasional
> "ker-splash" or "lickety-wop" along with what would become the more standard
> effects. Words as well as images became vehicles for carrying along his
> increasingly fast-paced storylines.
>
> *from "Storytelling in the Pulps, Comics, and Radio", by Tim DeForest*

The Batman TV show adopted this technique both as an homage to the comic book origins of the story and also to make poorly choreographed fight scenes look more exciting.

I was working on a silly project (to be documented at some future point) that involved buttons and a small [SSD1306] display. This is a 128x64 I²C addressable black-and-white display, widely supported by many languages. I thought it would be fun for a button press to result in a Batman-style onomatopoetic fighting word to show up on the display. This required solving two problems:

[SSD1306]: https://cdn-shop.adafruit.com/datasheets/SSD1306.pdf

1. Finding a list of onomatopoetic fighting words
2. Generating 128x64 images that look comic-like
3. Displaying the images on the SSD1306

## Finding word lists

This was the easy part -- several people have constructed lists of all the fighting words used in the Batman TV show. See e.g. [1], [2], [3].

[1]: https://batman60stv.fandom.com/wiki/Onomatopoeia
[2]: https://www.66batmania.com/trivia/bat-fight-words/
[3]: https://www.fastcompany.com/3055253/every-batman-fight-scene-onomatopoeia-in-one-alphabetical-gif

I have augmented this list with a collection of additional words, notably from the inimitable [Don Martin], who populated his comics in [Mad Magazine] with a variety of onomatopoetic words:

[don martin]: https://en.wikipedia.org/wiki/Don_Martin_(cartoonist)
[mad magazine]: https://en.wikipedia.org/wiki/Mad_(magazine)

{{< figure src="martin_don_ono.jpg" caption="From https://www.lambiek.net/artists/m/martin_don.htm" >}}

## Generating images

I turned to Python and the [Pillow] library to generate the requisite images. You can find the result in my [fightingwords] repository. Provide the code with an (optional) list of fonts and a file containing a list of words, and for each word it reads it will select a random font from your list, render the word, and apply some random transformations (one or more of shear, fisheye, or perspective transforms).

[pillow]: https://pillow.readthedocs.io/en/stable/?badge=latest
[fightingwords]: https://github.com/larsks/fightingwords

For example, if we were to run the following command:

```sh
python fight_word_generator.py \
  --font "Super Frosting,Badaboom BBMore JanuaryFirst DrawRetro Podcast,DINOUS,Besty Land,Green Town" \
  --negate \
  <(printf 'BAM!\nPOW!\nZAP!\n')
```

The results might look something like this:

![BAM!](BAM.png)
![POW!](POW.png)
![ZAP!](ZAP.png)

Every time you run it you'll get something a little different.

Because the image transformations are somewhat CPU intensive, there is a `gen-words.sh` script that wraps the `fight_word_generate.py` script to parallelize processing the entire list of words in the `words.txt` file:

```sh
#!/bin/sh

tmpdir=$(mktemp -d ./wordsXXXXXX)
trap 'rm -rf $tmpdir' EXIT
split -l5 words.txt "$tmpdir/words-"
mkdir -p output
find "$tmpdir" -type f -print0 |
  xargs -n1 -P0 -r -0 uv run fight_word_generator.py \
    --font "Super Frosting,Badaboom BBMore JanuaryFirst DrawRetro Podcast,DINOUS,Besty Land,Green Town" \
    --negate \
    --output output
```

This splits the list of words into groups of 5, and then spawns a new process for each group of five words.

## Displaying the images

Now that I had a set of appropriate images, I needed a way to display them on an SSD1306 display. I was working with a bunch of Go code at the time, so I implemented a small library and command line tool that you can find in my [display1306] repository. This code can display either text or graphics, and includes a virtual display driver (realized as an embedded web server) for testing when you don't have the hardware handy (I needed this because while I was deploying onto a raspberry pi, I was developing on a much more capable system without the ability to attach an SSD1306 display).

[display1306]: https://github.com/larsks/display1306

To demo this code using the virtual display driver, pass the `-n` option to the `display1306` command. For example:

```sh
display1306 -n --wait 'This is' 'a test' '******'
```

The `--wait` flag is necessary for one-off invocations that exit immediately; later on we'll set up looping demos for which this isn't necessary. You'll see the following in your terminal:

```
2025/10/11 15:25:31 Waiting for start button click in browser...
2025/10/11 15:25:31 SSD1306 Display Simulator running at http://localhost:8080
2025/10/11 15:27:49 Start button clicked, beginning rendering...
2025/10/11 15:27:49 paused; press CTRL-C to exit
```

Point your browser at <http://localhost:8080>, which will give you:

{{< figure src="display1306_initial.png" >}}

Click on the "Start Display" button, and you'll see:

{{< figure src="display1306_this_is_a_test.png" >}}

When displaying images, you can set up a loop using `--loop` and `--image-interval` options. For example, to display all of the fighting words images generated by the `gen-words.sh` script in the previous section, we could run:

```sh
ls output | shuf | xargs display1306 -n --image --image-interval 2s --loop
```

Which gets us:

{{< figure src="display1306_fightingwords.gif" >}}

Here's a video of the same thing running on the actual hardware:

{{< figure src="display1306_hardware.gif" >}}
