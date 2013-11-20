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

golab.domain.buoyancy = 
	{ name: 'buoyancy',
	  description: 'Buoyancy is an upward force exerted by a fluid.',
	  object_properties: [
	      { name: 'mass',
		type: 'magnitude',
		symbol: 'm',
		unit: 'kg'
	      },
	      { name: 'volume',
		type: 'magnitude',
		symbol: 'V',
		unit: 'm^3'
	      },
	      { name: 'density',
		type: 'magnitude',
		symbol: 'rho',
		unit: 'kg / m^3'
	      },
	      { name: 'material',
		type: 'multitude',
		values: '*'
	      },
	      { name: 'shape',
		type: 'multitude',
		values: '*'
	      }
	  ],
	  object_relations: [
	      { name: 'density',
		object_properties: [ 'density', 'mass', 'volume' ],
		relation: 'density = mass / volume'
	      }
	  ],
	  system_properties: [
	      { name: 'fluid_aquarium',
		type: 'multitude',
		values: '*'
	      },
	      { name: 'fluid_density',
		type: 'multitude',
		symbol: 'rho',
		unit: 'kg / m^3'
	      },
	      { name: 'fluid_column',
		type: 'multitude',
		symbol: 'h',
		unit: 'm'
	      }
	  ],
	  object_measures: [
	      { name: 'water_displacement',
		type: 'magnitude',
		unit: 'm^3',
		depends_on: {
		    object_properties: ['mass'],
		    system_properties: ['fluid_density']
		}
	      },
	      { name: 'sink_or_float',
		type: 'multitude',
		values: ['sinks', 'floats'],
		depends_on: {
		    object_properties: ['density'],
		    system_properties: ['fluid_density']
		}
	      }
	  ]
	};

golab.experiment = golab.experiment || {};

golab.experiment.Archimedes =
    { name: 'Archimedes',
	  description: 'Simulation-based version of the buoyancy experiment',
	  domain: 'buoyancy',
	  object_property_selection: ['mass', 'volume', 'shape'],
	  object_measure_selection: ['sink_or_float', 'water_displacement'],
	  system_property_selection: ['fluid_aquarium'],
	  object_property_specification: [
	      { property: 'mass',
		initial: 300,
		unit: 'gram',
		range: { minimum: 50, 
			 maximum: 500,
			 increment: 50
		       }
	      },
	      { property: 'volume',
		initial: '200',
		unit: 'cm_3',
		range: { minimum: 50, 
			 maximum: 500,
			 increment: 50
		       }
	      },
	      { property: 'shape',
		initial: 'sphere',
		values: ['sphere', 'cube']
	      }
	  ],
	  system_property_values: [
	      { property: 'fluid_aquarium',
		value: 'water'
	      },
	      { property: 'density',
		value: 1.0
	      }
	  ]
	};

