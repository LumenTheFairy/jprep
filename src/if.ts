/*$ note test basic if/else */
/*$ define test */
/*$ if test */
let x = 'test';
/*$ else */
let x = 'not test';
/*$ fi */
/*$ undefine test */
/*$ if test */
let y = 'test';
/*$ else */
let y = 'not test';
/*$ fi */

/*$ note test elseif */
/*$ define choice = thing1 < thing1, thing2, thing3, thing4 */
/*$ if choice = thing1 */
let a = 1;
/*$ elseif choice = thing2 */
let a = 2;
/*$ elseif choice = thing3 */
let a = 3;
/*$ else */
let a = 4;
/*$ fi */
/*$ define choice = thing2 */
/*$ if choice = thing1 */
let b = 1;
/*$ elseif choice = thing2 */
let b = 2;
/*$ elseif choice = thing3 */
let b = 3;
/*$ else */
let b = 4;
/*$ fi */
/*$ define choice = thing3 */
/*$ if choice = thing1 */
let c = 1;
/*$ elseif choice = thing2 */
let c = 2;
/*$ elseif choice = thing3 */
let c = 3;
/*$ else */
let c = 4;
/*$ fi */
/*$ define choice = thing4 */
/*$ if choice = thing1 */
let d = 1;
/*$ elseif choice = thing2 */
let d = 2;
/*$ elseif choice = thing3 */
let d = 3;
/*$ else */
let d = 4;
/*$ fi */

/*$ note test config */
/*$ if mode = debug */
let m = 'debug';
/*$ else */
let m = 'release';
/*$ fi */
