let x = 0; /*$note this gets deleted, leaving the rest of the line*/
let y = 0; /*$note this gets deleted /* /* /* still */
/*$note this gets deleted, removing the full line*/
    /*$note this gets deleted, removing the full line, even though there is indentation*/
/*$note however, the following blank line is preserved*/

/*$note this
is
a
multi
line
directive*/
/*$   note whitespace before the directive */
/*$
note the directive can be on a different line
*/
/*$ NOTE case doesn't matter on directive names */
/*$ NoTe case doesn't matter on directive names */
/*$ nOtE case doesn't matter on directive names */
/*$note the following lines have nothing special and should quickly be written out*/
let z = [
  0,
  1,
  2,
  3,
  ];
let s1 = "Text with /*$note something like this*/ keeps it"; /*$note but this is gone*/
let s2 = 'Text with /*$note something like this*/ keeps it, regardless of the quote'; /*$note but this is gone*/
let s3 = "Multi\
line\
strings\
/*$note are not a problem*/"; /*$note but this is gone*/
let s4 = "Text \" with /*$note escape characters*/"; /*$note gone*/
let s5 = 'Text \' with /*$note escape characters*/'; /*$note gone*/
let s6 = /*$note surrounded*/"/*$note text*/"/*$note surrounded*/;
// /*$note this line comment is preserved*/
let a = 0; // /*$note this line comment is also preserved*/
/* /*$note this block comment is preserved */
let b = 0; /* /*$note this block comment is also preserved */
/* this
block
/*$note comment
is
preserved */
let s7 = `Template literal keeps /*$note*/`; /*$note gone*/
let s8 = `Template literal with \` keeps /*$note*/`; /*$note gone*/
let s9 = `I say: "${ z /*$note nothing*/}" /*$note something*/`; /*$note gone*/
let s10 = `I say: "\${ /*$note this stays*/ }"`; /*$note gone*/
let s11 = `I say: "$\{ /*$note this stays*/ }"`; /*$note gone*/
let s12 = `I say: "${ a /*$note nothing*/}" /*$note something*/ and "${ b /*$note nothing*/}/*$note something*/"`; /*$note gone*/
let s13 = `I say: "${
  {test: 5/*$note nothing*/} /*$note nothing*/
}" /*$note something*/`; /*$note gone*/
let s15 = `I say: "${
  {test: `nested ${
    {test: {test: 5/*$note nothing*/}, /*$note nothing*/x: 6}
  }`/*$note nothing*/} /*$note nothing*/
}" /*$note something*/`; /*$note gone*/
