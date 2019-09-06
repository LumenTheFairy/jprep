A directive takes the form
```
/*$Directive*/
```
There cannot be any whitespace before the `$`, (the result would just be a normal comment). There can be any amount of whitespace surrounding the Directive, including newlines. Directives do not need to be at the start of a line. If this construct appears inside a comment, it is not considered a directive. If this construct appears inside a string, it is not considered a directive (if you need directives in the middle of a sting, use template literals and place the directive inside a template expression).

Broadly speaking, there are three categories of directives:
- Definitions
- Conditions
- Comments

The Definition directives are
```
/*$define NAME [= VALUE] [< CHOICE1, CHOICE2, CHOICE3, ...] */
/*$undefine NAME */
```

`NAME`, `VALUE`, and any `CHOICE` must be valid identifiers. Casing is not important for these identifiers, or for "define" or "undefine". Defining a name places that name in a definition environment, optionally mapping it to a value. If the name is already in the definition environment, redefining it without a value will remove any value it has (but leave it defined), and redefining it with a value will change its value. If choices are present, as long as the name is defined, it's value can only be set to one of the choices, and it can only be compared to these choices in conditions. It is an error to give choices to a name that already has them. Giving explicit choices for a name can help catch typos in conditions. Undefining a name will remove it from the definition environment. A name can only be undefined at the same scoping level as where it was defined. When a definition goes out of scope, it is automatically undefined (see scoping rules below).

#TODO: case sensitivity needs to be changed

Conditions take the form
```
/*$if NAME1 [= VALUE1] */ Code [/*$elseif NAME2 [= VALUE2]*/ Other Code ...] [/*$else*/ More Code] /*$fi*/
```

Again, `NAME` and `VALUE` must be valid identifiers, and casing is not important for them, or for any of the directive names. If a condition is just a name, it is true if that name is in the definition environment. If a condition is a name and a value, it is true if the name is defined and has the requested value. If a name has been defined to have choices, it is an error to use it in a condition without a value, and it is an error to compare it to a value that was not one of its choices. Code is carried over to output if the condition holds, and stripped out otherwise, following usual if..else if..else..fi control flow. The enclosed code can contain other directives, but it must start and end at the same scope level (see scoping rules below).

Comments take the form
```
/*$note Comment*/
```
("Note" is required, and all following text can be anything). Casing is not important for "note". These directives do nothing, but they are stripped out. Use these to write comments that you don't want to appear in the preprocessed code, for example, comments that document the use of other directives. If the note is the only thing on a line besides whitespace, the full line is stripped out.


Scoping:

In jprep, definitions are basically lexically scoped with respect to the JavaScript/TypeScript code. That is, a definition is only valid for the file, function, block, or object literal it is defined in (and any nested scopes therein). I say "basically" lexically scoped because object literals increasing scope depth is not typical. Another way to think of it is: any '{' outside strings, comments, and directives increases the scope depth, and likewise any '}' decreases it.

#TODO: be more clear on definition scope shadowing behavior


Configuration:

The configuration file, if any, is processed first. All definitions in this file are in scope for the preprocessing of all other files (and cannot be undefined by any of them).
