/*  $Id$	-*- mode: javascript -*-
 *  
 *  File	buoyancy.js
 *  Part of	Go-Lab Experimental Design Tool
 *  Author	Anjo Anjewierden, a.a.anjewierden@utwente.nl
 *  Purpose	Description of buoyancy domain and experiments
 *  Works with	JavaScript
 *  
 *  Notice	Copyright (c) 2013  University of Twente
 *  
 *  History	15/04/13  (Created)
 *  		10/06/13  (Last modified)
 */ 

/*------------------------------------------------------------
 *  Directives
 *------------------------------------------------------------*/

//  For now
var golab = golab || {};

golab.domain = golab.domain || {};

golab.domain.{{ domain_name }} = {{ domain }} 

golab.experiment = golab.experiment || {};

golab.experiment.{{ experiment_name }} = {{ experiment }} 


function start_lab() {
  if (typeof(console) === 'undefined') {
    console = {};
    console.log = function () {};
  }
  edt.start({ domain: golab.domain.{{ domain_name }} ,
              experiment: golab.experiment.{{ experiment_name }} ,
	      confirm_flags: false
	   });
}
window.onload = function() { start_lab(); }
