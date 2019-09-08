# jprep

`jprep` is a JavaScript/TypeScript preprocessor. It's usage is as follows:
```
usage: jprep.py [-h] [-i IN_DIR] [-o OUT_DIR] [-c CONFIGURATION] [-b]
                [--verbose] [-v]
                files [files ...]

Preprocesses the given JavaScript/TypeScript files.

positional arguments:
  files                 list of files to preprocess

optional arguments:
  -h, --help            show this help message and exit
  -i IN_DIR, --in_dir IN_DIR
                        directory the input files are relative to (defaults to
                        "./")
  -o OUT_DIR, --out_dir OUT_DIR
                        directory in which to write the output files (defaults
                        to "./preprocessed/")
  -c CONFIGURATION, --configuration CONFIGURATION
                        configuration file which holds definitions that stay
                        in scope for all preprocessed files
  -b, --build_off       only preprocess files that can be determined to need
                        preprocessing
  --verbose             display additional information during preprocessing
  -v, --version         show program's version number and exit
```

## General
##### Directives
A directive takes the form
```
/*$Directive*/
```
There cannot be any whitespace before the `$`, (the result would just be a normal comment). There can be any amount of whitespace surrounding the Directive, including newlines. Directives do not need to be at the start of a line. If this construct appears inside a comment, it is not considered a directive. If this construct appears inside a string, it is not considered a directive (if you need directives in the middle of a sting, use template literals and place the directive inside a template expression).

Broadly speaking, there are three categories of directives:
- [Definitions](#defintions)
- [Conditions](#conditions)
- [Comments](#comments)

Directives themselves are stripped out of the code. If the directive is the only thing on a line besides whitespace, the full line is stripped out.

##### Scoping
In jprep, definitions are scoped with respect to the JavaScript/TypeScript code. Any '{' outside strings, comments, and directives enters a new scope, and the matching '}' leaves it (of note, expressions in template literals are at the same scope as the template literal itself; we consider the delimiting curly braces part of the string). Furthermore, a new scope is entered and left at the begining and end of each branch of an if directive structure.

##### Configuration
The configuration file, if any, is processed first. The definitions in this file are in scope for the preprocessing of all other files (and cannot be undefined by any of them).

## Directives
#### Definitions
The Definition directives are
```
/*$define NAME [= VALUE] [< CHOICE1, CHOICE2, CHOICE3, ...] */
/*$undefine NAME */
```

`NAME`, `VALUE`, and any `CHOICE` must be valid identifiers. Casing is not important for "define" or "undefine", but it is for these identifiers. Defining a name places that name in the current scope of the definition environment, optionally mapping it to a value. If the name is already in the current scope of the definition environment, redefining it without a value will remove any value it has (but leave it defined), and redefining it with a value will change its value. If the name is not in the current scope of the definition environment, but it is in a lower scope, the definition shadows that in the lower scope. If choices are present, as long as the name is defined at any existing scope, it's value can only be set to one of the choices, and it can only be compared to these choices in conditions. It is an error to give choices to a name that already has them. Giving explicit choices for a name can help catch typos in conditions. Undefining a name will remove it from the current scope of the definition environment. This also removes any choices assigned to that name if it is the lowest scope that contains it. A name can only be undefined in a scope where it was defined.

#### Conditions
Conditions take the form
```
/*$if NAME1 [= VALUE1] */ Code [/*$elseif NAME2 [= VALUE2]*/ Other Code ...] [/*$else*/ More Code] /*$fi*/
```

Again, `NAME` and `VALUE` must be valid identifiers, and casing is important for them, but not for the directive names. If a condition is just a name, it is true if that name is in the definition environment. If a condition is a name and a value, it is true if the name is defined and has the requested value (at the most recent scope with the name). If a name has been defined to have choices, it is an error to use it in a condition without a value, and it is an error to compare it to a value that was not one of its choices. Code is carried over to output if the condition holds, and stripped out otherwise, following usual if..else if..else..fi control flow. The enclosed brances can contain other directives. Each branch must start and end at the same scope level.

#### Comments
Comments take the form
```
/*$note Comment*/
```
("Note" is required, and all following text can be anything.) Casing is not important for "note". These directives do nothing, but they are stripped out. Use these to write comments that you don't want to appear in the preprocessed code, for example, comments that document the use of other directives.
