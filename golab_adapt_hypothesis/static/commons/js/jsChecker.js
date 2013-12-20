/**
 * Created with IntelliJ IDEA.
 * User: sikkenj
 * Date: 19-2-13
 * Time: 17:07
 */

"use strict";

if (typeof console === "undefined") {
//   alert("console is not defined!")
   Console = function () {
      this.log = function (message) {
//         alert(message)
      }
   }
   console = new Console()
//   console.log("created a new console")
}

