/*  $Id$	-*- mode: javascript -*-
 *  
 *  File	goodies.js
 *  Part of	JavaScript
 *  Author	Anjo Anjewierden, a.a.anjewierden@utwente.nl
 *  Purpose	Goodies for JavaScript
 *  Works with	JavaScript
 *  
 *  Notice	Copyright (c) 2013  University of Twente
 *  
 *  History	16/04/13  (Created)
 *  		18/04/13  (Last modified)
 */ 

/*------------------------------------------------------------
 *  Directives
 *------------------------------------------------------------*/

String.prototype.capitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
}


