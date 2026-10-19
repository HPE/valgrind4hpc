# `textcheck.py`

`textcheck.py` has a function called `compare_files(reference file, output file)` which takes two file paths and compares their contents. The `reference file` argument is a `.txt` file path with some optional markup (explained below) and the `output file` argument is a `.out` file path which is the raw output of some binary that was being tested. It returns the result of a text matching test as a tuple: `(Success, Error message)`. A successful test will return `(True, "")`, while a failed test will return `(False, "...error message here...")`

## Example

The basic idea is to have a desired output that represents a test passing. For example, if we had a very simple program which simply output "Hello world!" and we wanted to test it, we could set up the following `.txt` file:

`example1.txt`
```
Hello world!
```

Once the test is run, we capture the output in a file called `example1.out`:

`example1.out`
```
Hello world!
```

Once these two files are on the file system, we use the text comparison function to test them:

```
class HelloTest(Test):
    def test(self):
        ... run test ...
        result, error = cdst_test.textcheck.compare_files("example1.txt", "example1.out")
        self.assertTrue(result, error)
```

In this trivial example, we simply match the line "Hello world!" with whatever line comes out of the testing program. Some test cases can become more complicated however, posing problems such as inconsistent output ordering/content or output differing between machines. This is why markup is useful.

## Markup Example

Here is a small example of how you can use a `.txt` file with markup to match an `.out` output file.

Our hello world program has gotten more advanced and now outputs the same old "Hello world!" as before, but now it outputs the system hostname after it. How can we write a single test that would work on any machine? This is the perfect opportunity to use a wildcard markup.

```
Hello World!
%*
```

This `.txt` file would match the following `.out` file:

```
Hello World!
pegasus
```

Or this one...

```
Hello World!
jupiter
```

Or even this one:

```
Hello World!
you need to be careful with wildcards!
they can match multiple lines!
```

## Markup Documentation

The wildcard is one of the many markup symbols available. Here are details on every markup symbol available.

### Unordered Section: `%< %- %>`

This section denotes sections of text that could be output in any order. The beginning of an unordered section is denoted by `%<`, sections are split by `%-`, and the end of an unordered section is denoted by `%>`. There can be an arbitrary amount of middle sections.

```
%<
hello world from rank 0
%-
hello world from rank 1
%-
hello world from rank 2
%>
```

This would match the following:

```
hello world from rank 0
hello world from rank 1
hello world from rank 2
```

and:

```
hello world from rank 2
hello world from rank 0
hello world from rank 1
```

But it would not match the following:

```
hello world from rank 0
hello world from rank 2
this text doesn't belong...
hello world from rank 1
```

Individual parts of an unordered section can contain multiple lines. The lines in a multiple line part of an unordered section must appear in the order they are written, but can be mixed with other parts of the unordered section.

```
%<
hello world from rank 0
goodbye world from rank 0
%-
hello world from rank 1
goodbye world from rank 1
%-
hello world from rank 2
goodbye world from rank 2
%>
```

This would match the following:

```
hello world from rank 0
goodbye world from rank 0
hello world from rank 2
goodbye world from rank 2
hello world from rank 1
goodbye world from rank 1
```

Or even this:

```
hello world from rank 2
hello world from rank 1
goodbye world from rank 1
goodbye world from rank 2
hello world from rank 0
goodbye world from rank 0
```

But not this:

```
goodbye world from rank 0
hello world from rank 0
hello world from rank 1
goodbye world from rank 1
hello world from rank 2
goodbye world from rank 2
```

This doesn't match because "goodbye world from rank 0" came before "hello world from rank 0" Since there was an order for these two lines defined in the part of the unordered section they were in, they are incorrect.

### Wildcard Section: `%*`

Much like a wildcard in a regular expression, this markup matches any line. The wildcard section can also match multiple lines. It is useful to put at beginnings and ends of `.txt` files to catch any "job queued, please wait" messages that sometimes get emitted by WLMs. It's also useful to remove any part of the program output that simply isn't that important to a particular test.

```
%*
I'm just looking for this one line in a jungle of other lines!
%*
```

Matches

```
Scary spider
I'm just looking for this one line in a jungle of other lines!
Mighty lion
```

And even

```
Scary spider
Scary spider's friend
I'm just looking for this one line in a jungle of other lines!
Mighty lion
Mighty lion's brother
```

But not:

```
Scary spider
Scary spider's friend
Whoops, the line I actually want isn't here any more...
Mighty lion
Mighty lion's brother
```

### Ignore Section: `%[`, `%]`

The ignore section can be used to say "Starting now, ignore any output that looks like this. Don't even feed it to the other sections". This is useful to ignore things like debug output.

```
This line is required...
%[
Distraction
Annoyance
Garbage
%]
And this line is required too.
```

Matches

```
This line is required...
Distraction
Garbage
And this line is required too.
Annoyance
Annoyance
```

But not

```
Distraction
This line is required...
Annoyance
Garbage
And this line is required too.
```

Because "Distraction" came before the line there the ignore section was defined, so it wasn't being ignored yet. "Distraction" does not match "This line is required...", so the overall result is a mismatch.

This section is particularly useful when combined with regular expressions (see below). For example, to ignore all output lines that start with "DEBUG:", you could do this:

```
%[
DEBUG:%.*%
%]
Important lines
Don't miss em
```

To match this:

```
DEBUG: starting app...
DEBUG: success.
DEBUG: so how about that weather lately?
Important line
Don't miss em
DEBUG: shutting down...
```

### Comment Section: `%#`

Simply denotes a comment in the `.txt` file. Does not match up to anything in the `.out` file.

```
%# This cool test was written by josh!
Actual lines...
... to match
```

Matches:

```
Actual lines...
... to match
```

### Regular Expressions: `% %`

If you don't know the exact expected text, but know the nature of it, you can use a regular expression instead of raw text. Regular expressions work in any of the above sections on any point in the line.

```
%# Match 3 two digit even numbers.
%\d[02468]%
%\d[02468]%
%\d[02468]%
%# Match anything ending in "The end."
%.*The end\.%
```

Matches:

```
22
44
66
And they lived happily ever after. The end.
```

### Text Substitutions

Sometimes it's useful to be able to use values that change from machine to machine, such as hostname or current working directory. Right now, there is only one text substitution that's used, but if you need one in the future, you can easily add it to the `compare_lines` function in `textcheck.py`.

| Markup        | Meaning                                           | Example Markup      | Could Resolve To                           |
|-              |-                                                  |-                    |-                                           |
| `%%testdir%%`	| Current working directory that tests are run from | `%%testdir%%/bd_dt` | `/home/users/chandlej/gdb4hpc-tests/bd_dt` |
