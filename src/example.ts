let x = 0; /*$note this gets deleted, leaving the rest of the line*/
let y = 0; /*$note this gets deleted /* /* /* still */
/*$note this gets deleted, removing the full line*/
    /*$note this gets deleted, removing the full line, even though there is indentation*/
/*$note however, the following blank line is preserved*/

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
