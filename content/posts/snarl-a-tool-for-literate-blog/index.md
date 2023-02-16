---
categories:
- tech
date: '2020-01-15'
filename: 2020-01-15-snarl-a-tool-for-literate-blog.md
tags:
- literate-programming
- markdown
title: 'Snarl: A tool for literate blogging'
---

[Literate programming][] is a programming paradigm introduced by Donald Knuth in which a program is combined with its documentation to form a single document. Tools are then used to extract the documentation for viewing or typesetting or to extract the program code so it can be compiled and/or run. While I have never been very enthusiastic about literate programming as a development methodology, I was recently inspired to explore these ideas as they relate to the sort of technical writing I do for this blog.

[literate programming]: https://en.wikipedia.org/wiki/Literate_programming

My previous post was about [OVN and DHCP][]. While I had tested out configuration in question prior to writing the article, I introduced some code changes in the article without testing them, and that resulted in some [dumb errors][]. It occurred to me that some of the same tooling that had been designed for literate programming may offer a mechanism by which I could extract and test code in my blog posts to ensure that the code I was presenting operates as described.

[dumb errors]: https://github.com/larsks/blog.oddbit.com/issues/8#issuecomment-572824924
[ovn and dhcp]: {{< ref "ovn-and-dhcp" >}}

Unfortunately, many of the [existing literate programming tools][tools] weren't going to work out. Several of them assume you want to write documentation in LaTeX. Others are designed primarily for a particular programming language, and just about all of them use syntax that doesn't really play well with Markdown documents. The tool that came closest was [lmt][], but that tool only addresses the "tangling" aspect of document processing (extracting code), whereas I explicitly want the ability to exclude some code from the finished documentation, which requires support for "weaving" (documentation extraction).

[lmt]: https://github.com/driusan/lmt
[tools]: http://www.literateprogramming.com/tools.html

Since I couldn't find a tool that did exactly what I wanted, I ended up writing my own.

## Introducing Snarl

[Snarl][] is a tool for writing literate blog posts. It's primary purpose is to permit you to extract code from a Markdown document in order to test it and ensure its accuracy. It has feature similar to many other literate programming tools:

- You can present code in an order that differs from that which you output for testing. This allows you to present code in the way that makes the most sense for your readers, rather than that required by the particular programming language you're using.
- Code blocks can refer to other code blocks. These references are expanded when writing the content to files.
- Snarl supports an "include" feature that permits you to split up a large document across multiple files.

[snarl]: https://github.com/larsks/snarl

## Code blocks

The heart of Snarl is the code block, which uses an extended form of the standard Markdown fenced code block:

    ```[<language>]=<label> [--file] [--hide] [--tag tag [...]] [--replace
    <pattern> <substitution>]
    ...code goes here...
    ```

The `<language>` information is optional and is ignored by Snarl; this is standard syntax for providing syntax coloring hints for fenced code blocks. The value is passed on to the rendered Markdown when running `snarl weave`.

Everything after the `=` is interpreted using a standard command-line option parser (Python's [argparse][] module), which means that `<label>` may contain whitespace as long as you quote it.

The options are:

- `--file` (`-f`) -- mark a code block as a file. Blocks marked as files will be written out by default when running `snarl tangle`.

- `--hide` (`-h`) -- Elide this block when running `snarl weave`.

- `--tag <tag>` (`-t tag`) -- Apply a tag to the code block. You can elect to write out only certain code blocks using the `--tag` option to `snarl tangle`.

- `--replace <pattern> <subsitution>` -- Replace regular expression `<pattern>` with `<substitution>` when tangling the document.

[argparse]: https://docs.python.org/3/library/argparse.html

## A simple example

Let's say we were going to write a post about a "Hello world!" program in C.  Our document might look something like this:

<pre>
## Printing text to the console

To print the phrase &quot;Hello, world!&quot; to the console, we can use the `printf`
function, like this:

```c=&quot;print hello&quot;
printf(&quot;Hello, world!\n&quot;);
```

If we wrap this in a function, we get:

```c=&quot;main function&quot;
int main(int argv, char **argc) {
  &lt;&lt;print hello&gt;&gt;

  return 0;
}
```

In order to avoid problems and compiler warnings, we really ought to include
the `stdio.h` header file before referring to the `printf` function:

```c=&quot;include header files&quot;
#include &lt;stdio.h&gt;
```

```c=hello.c --file --hide
// This file was generated using snarl.

&lt;&lt;include header files&gt;&gt;

&lt;&lt;main function&gt;&gt;
```
</pre>

### Tangling

If we were to run `snarl tangle` on this file, we would get as output a single file, `hello.c`, with the following content:

<pre>
// This file was generated using snarl.

#include &lt;stdio.h&gt;

int main(int argv, char **argc) {
printf(&quot;Hello, world!\n&quot;);

  return 0;
}
</pre>

This file contains the contents of the `include header files` block and the `main function` block, along with some literal content from the `hello.c` block itself.

It would be trivial to have a simple shell script compile and execute this code to ensure that it behaves as expected.

### Weaving

Running `snarl weave` on the document source would result in:

<pre>
## Printing text to the console

To print the phrase &quot;Hello, world!&quot; to the console, we can use the `printf`
function, like this:

```c
printf(&quot;Hello, world!\n&quot;);
```

If we wrap this in a function, we get:

```c
int main(int argv, char **argc) {
  &lt;&lt;print hello&gt;&gt;

  return 0;
}
```

In order to avoid problems and compiler warnings, we really ought to include
the `stdio.h` header file before referring to the `printf` function:

```c
#include &lt;stdio.h&gt;
```

</pre>

You can see that the Snarl-annotated code blocks have been rendered as standard Markdown fenced code blocks without the additional metadata. You can also see the effect of the `--hide` option on code blocks: the contents of `hello.c` are excluded in the final Markdown output.

## A longer example

The [source][] to my earlier blog post on [OVN and DHCP][] provides a less contrived example. In addition to the document source itself, you can see the framework I used for running the scripts presented in the post and testing the environment afterwards.

### Using replace

That post provides an example of using the `--replace` flag on a code block. For the purposes of the article, I was using fixed IP addresses for the nodes involved, but when setting up a virtual environment for testing it was easier to just let the nodes pick up addresses dynamically. In order to test the code that uses a static ip address, I replace that address with a variable reference when generating the script files:

    ```=configure_ovs_external_ids --replace 192.168.122.100 ${OVN0_ADDRESS}
    ovs-vsctl set open_vswitch .  \
      external_ids:ovn-remote=tcp:192.168.122.100:6642 \
      external_ids:ovn-encap-ip=$(ip addr show eth0 | awk '$1 == "inet" {print $2}' | cut -f1 -d/) \
      external_ids:ovn-encap-type=geneve \
      external_ids:system-id=$(hostname)
    ```

When running `snarl tangle` on that document, the above text renders as:

```
ovs-vsctl set open_vswitch .  \
  external_ids:ovn-remote=tcp:${OVN0_ADDRESS}:6642 \
  external_ids:ovn-encap-ip=$(ip addr show eth0 | awk '$1 == "inet" {print $2}' | cut -f1 -d/) \
  external_ids:ovn-encap-type=geneve \
  external_ids:system-id=$(hostname)
```

### Using tags

If you look at the files embedded in that post, you will find that they are tagged using the `--tag` (`-t`) option:

    ```=configure-common.sh --file --hide -t setup
    <<enable_common_services>>
    <<add_br_int>>
    ```

This permits me to extract a subset of files. For example, to extract just the files tagged `setup`, I would run:

```
snarl tangle -t setup 2019-12-19-ovn-and-dhcp.snarl.md
```

[source]: https://raw.githubusercontent.com/larsks/blog.oddbit.com-snarl/master/ovn-and-dhcp/2019-12-19-ovn-and-dhcp.snarl.md

## Including files

While the main focus of Snarl is extracting code from documentation, sometimes you want to go in the other direction. Snarl supports an `include` directive that will include the content of another file in the current document. The `include` directive is written as an HTML comment:

```
<!-- include <path> [--escape-html] [--verbatim] -->
```

A simple example might look like:

```
<!-- include anotherfile.md -->
```

By default, the file contents will be processed as if they were part of the existing document. That means that your included file may itself contain Snarl directives. This isn't always the behavior that you want, so there are a couple of options available that modify the behavior of `include`.

In order to embed Snarl samples in this post, I am using the HTML `<pre>` element to wrap the sample text, which I am including in this document via the `include` directive. I don't want to interpret Snarl directives in these included files.  The `--verbatim` (or `-v`) option will include the literal content of the named file without looking for Snarl directives.

An unfortunate side effect of using the `<pre>` element is that I have to escape any `<` characters that appear in the included content. The `--escape-html` (or `-e`) option performs the necessary HTML escaping on the included file so that it will display as intended.

For example, the example Snarl source presented earlier in this document was included using the following syntax:

```
<!-- include hello.snarl.md -ve -->
```

## To infinity and beyond

Being able to extract and verify code in technical articles is incredibly useful. There are other tools out there that will do something similar, but I'm happy with how Snarl operates. I will absolutely be using this going forward to avoid unfortunate errors in my blogs posts, and I hope others will find it useful as well.