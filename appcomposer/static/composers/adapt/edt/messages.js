/*  $Id$        -*- mode: javascript -*-
 *  
 *  File        messages.js
 *  Part of     Go-Lab Experimental Design Tool
 *  Author      Anjo Anjewierden, a.a.anjewierden@utwente.nl
 *              Siswa van Riesen, s.a.n.vanriesen@utwente.nl
 *  Purpose     Messages with translations in various languages
 *  Works with  JavaScript
 *  
 *  Notice      Copyright (c) 2013  University of Twente
 *  
 *  History     15/04/13  (Created)
 *              10/06/13  (Last modified)
 */ 

/*------------------------------------------------------------
 *  Directives
 *------------------------------------------------------------*/

var edt = edt || {};

edt.messages = (function() {
    function lab(obj, noendspace) {
        return ' <span class="domain_term">' + obj.label() + '</span>' +
	    (noendspace ? '' : ' ');
    };

    function lc(obj, noendspace) {
        return ' <span class="domain_term">' + obj.label(true) + '</span>' +
	    (noendspace ? '' : ' ');
    };

    function labsc(vars, con) {
	var len = vars.length;

	switch (len) {
	case 0:	return '';
	case 1: return lc(vars[0], true);
	case 2: return lc(vars[0], true) + ' ' + con + ' ' + lc(vars[1],true);
	}

	var str = '';
	for (var i=0; i<len-1; i++) {
	    str += lc(vars[i],true) + ', ';
	}
	str += ' ' + con + ' ' + lc(vars[len-1],true);
	return str;
    };

    var msg = {};

    msg.plan_modifications_incompatible = {
	en: 'The modifications you made to the plan are incompatible ' +
	    'with the previous design you created. ' +
	    'Create a new design based on the new plan.',
	nl: 'De veranderingen die je hebt gemaakt in het plan komen niet ' +
	    'overeen met het huidige ontwerp. ' +
	    'Maak een nieuw ontwerp op basis van het nieuwe plan.'
    };

    msg.too_many_independent_variables = {
        en: function() {
	    return 'You want to vary' + this.vars.length + ' variables. ' +
		'It is only possible to vary at most two variables at the same time.';
	},
        nl: function() {
	    return 'Je wilt' + this.vars.length + ' variabelen vari&euml;ren. ' +
		'Je kunt maximaal twee variabelen tegelijkertijd vari&euml;ren';
	}
    };

    msg.multiple_independent_variables = {
        en: function() {
            return 'You want to vary' + labsc(this.vars, this.conjunction) + '. ' +
                'If you vary more than one variable, you cannot be sure what ' +
                'causes the effect of the observed/measured variable. ' +
                'However, sometimes an effect is only found when two variables ' +
                'interact with each other because these variables form ' +
                'one concept together (e.g. speed = distance/time).';
        },
        nl: function() {
            return 'Je wilt' + labsc(this.vars, this.conjunction) + ' vari&euml;ren. ' +
                'Als je meer dan &eacute;&eacute;n concept tegelijkertijd varieert, weet je niet zeker wat ' +
                'het effect op de geobserveerde/gemeten variabele veroorzaakt. ' +
                'Let op, soms be&iuml;nvloeden twee variabelen elkaar omdat zij samen &eacute;&eacute;n concept vormen ' +
				'en vind je alleen een effect wanneer je allebei deze variabelen varieert ' +
                '(bijvoorbeeld: snelheid = afstand/tijd).';
        }
    };

    msg.multiple_control_variables = {
        en: 'You want to keep multiple variables the same across experimental runs. ' + 
            'This is good because it limits unwanted influences on ' +
            'the observed/measured variable.',
        nl: 'Je wilt meerdere variabelen hetzelfde houden tussen experimenten. ' + 
            'Dit is goed omdat je hierdoor ongewenste invloeden op de ' +
            'geobserveerde/gemeten variabele beperkt.'
    };

    msg.multiple_roles_for_a_variable = {
        en: function() {
            return 'You cannot vary' + lc(this) +
                '<b>and</b> keep it the same at the same time.';
        },
        nl: function() {
            return 'Je kunt' + lc(this) + 'niet tegelijkertijd vari&euml;ren ' +
                '<b>en</b> hetzelfde houden.';
        }
    };

    msg.confirm_drop_independent = {
        en: function () { 
            return 'You want to vary' + lc(this) +
                'across experimental runs. ' +
                'This means that you want to research the effect of' + lc(this) +
                'on the variable you place in observe/measure.'
        },
        nl: function () { 
            return 'Je wilt' + lc(this) + 'vari&euml;ren ' +
                'tussen experimenten. ' +
                'Dit betekent dat je het effect van' + lc(this) +
                'op de variabele die je in observeer/meet plaatst wilt onderzoeken.'
        }
    };

    msg.confirm_drop_control = {
        en: function () { 
            return 'You want to keep ' +
                lc(this) + ' the same across experimental runs. ' +
                'This means that you want it to have no influence on the variable ' +
                'you place in observe/measure.'
        },
        nl: function () { 
            return 'Je wilt ' +
                lc(this) + ' hetzelfde houden tussen experimenten. ' +
                'Dit betekent dat je wilt dat dit geen invloed heeft op de variabele ' +
                'die je in observeer/meet plaatst.';
        }
    };

    msg.confirm_drop_dependent = {
        en: function () { 
            return 'You want to observe/measure ' + lc(this,true) + '. ' +
                'This means that you want to research the effect of the variable ' +
                'you vary on ' + lc(this,true) + '.';
        },
        nl: function () { 
            return 'Je wilt ' + lc(this) + 'observeren/meten. ' +
                'Dit betekent dat je wilt onderzoeken wat het effect is van ' +
                'de variabele die je varieert op ' + lc(this,true) + '.';
        }
    };

    msg.heuristics_design = {
        en: '<p><ul>' +
            '<li>Make use of simple values.</li>' +
            '<li>Choose equal increments.</li>' +
            '<li>Conduct the same experimental run several times to account for measurement errors.</li>' +
            '<li>Make use of extreme values.</li>' +
            '</ul></p>',
        nl: '<p><ul>' +
            '<li>Maak gebruik van simpele waarden.</li>' +
            '<li>Kies gelijke waardeverhogingen tussen experimenten.</li>' +
            '<li>Voer hetzelfde experiment meerdere keren uit om meetfouten op te vangen.</li>' +
            '<li>Maak gebruik van extreme waarden.</li>' +
            '</ul></p>'
    };

    msg.too_few_experimental_runs = {
        en: function () {
            return
            '<p>You only planned ' + this.number_of_runs + ' experimental runs. ' +
                'Plan at least ' + this.desired_runs + ' experimental runs.' +
                '</p>'
        },
        nl: function () {
            return
            '<p>Je hebt slechts ' + this.number_of_runs + ' experimenten gepland. ' +
                'Plan tenminste ' + this.desired_runs + ' experimenten.' +
                '</p>'
        }
    };

    msg.finished_all_experimental_runs = {
        en: function () {
            return '<p>' +
                'You executed all your experimental runs. ' +
                'You can create a chart to view your data graphically. ' +
                'This might help to draw conclusions or decide if you need ' +
                'to conduct more experiments.' +
                '</p>';
        },
        nl: function () {
            return '<p>' +
                'Je hebt al je experimenten uitgevoerd. ' +
                'Je kunt een grafiek cre&euml;ren om je data grafisch weer te geven. ' +
                'Dit kan je helpen bij het trekken van conclusies of bepalen of ' +
                'je meer experimenten nodig hebt.' +
                '</p>';
        }
    };

    msg.heuristics_plan = {
        en: '<ul>' +
            '<li>Design experiments to test your hypothesis.</li>' +
            '<li>Keep experiments simple.</li>' +
            '<li>Vary one thing at a time.</li>' +
            'Keep in mind that some variables are made up of multiple concepts ' +
            '(e.g., speed = distance / time).</li>' +
            '<li>Keep everything you do not measure the same across experiments.</li>' +
            '</ul>',
        nl: '<ul>' +
            '<li>Ontwerp experimenten om je hypothese te toetsen.</li>' +
            '<li>Houd experimenten gemakkelijk.</li>' +
            '<li>Varieer &eacute;&eacute;n ding tegelijk.</li>' +
            'Houd er rekening mee dat sommige variabelen uit meerdere concepten bestaan ' +
            '(bijvoorbeeld: snelheid = afstand/tijd).</li>' +
            '<li>Houd alles wat je niet meet hetzelfde tussen experimenten.</li>' +
            '</ul>'
    };

    msg.instructions_plan = {
        en: '<p>You will now start planning your experiment. ' +
            'Look at the hypothesis you will test. ' +
            'Then use the Experiment Design Tool and think about the variables you need to ' +
            '<em>observe/measure</em>, <em>vary</em> and <em>keep the same</em> in order to test your hypothesis. ' +
            'Drag those variables from "Select variables" to the appropriate place within ' +
            '"Design experiment".</p>' +
            '<p>If you place a variable in the wrong box, you can simply drag it ' +
            'to a different box, ' +
            'or remove it by dropping it in the background.</p>' +
            '<p>Click <span class="tool_term">Design</span> when you are finished.</p>',
        nl: '<p>Je gaat nu beginnen met het plannen van je experiment. ' +
            'Kijk naar de hypothese die je gaat toetsen. ' +
            'Gebruik daarna de Experiment Ontwerp Tool en bedenk welke variabelen je moet ' +
            ' <em>observeren/meten</em>, <em>vari&euml;ren</em> en <em>hetzelfde moet houden</em> om je hypothese te toetsen. ' +
            'Sleep de variabelen van "Selecteer variabelen" naar de juiste plaats binnen ' +
            '"Ontwerp experiment".</p>' +
            '<p>Als je een variabele in een verkeerd vak hebt geplaatst, kun je deze gemakkelijk ' +
            'naar een ander vak slepen, ' +
            'of verwijderen door deze naar een plek in de achtergrond te slepen.</p>' +
            '<p>Klik op <span class="tool_term">Ontwerp</span> wanneer je klaar bent.</p>'
    };

    msg.instructions_design = {
        en: function () {
            return '<p>' +
                'Now you will finalize planning your experiment by filling out the table. ' +
                'First select the value(s) of <span class="domain_term">' +
                lc(this.control) + '</span>. This value is the same for all ' +
                'experimental runs. ' +
                'Then add experimental runs and select a value for <span class="domain_term">' +
                lc(this.independent) + '</span>. This value is different per experimental run. ' +
                'After filling out the table, click <span class="tool_term">Run</span>.';
        },
        nl: function () {
            return '<p>' +
                'Nu maak je het plan voor je experimenten af door de tabel in te vullen. ' +
                'Bepaal eerst de waarde(n) van <span class="domain_term">' +
                lc(this.control) + '</span>. Deze waarde is hetzelfde voor alle ' +
                'experimenten. ' +
				'Voeg daarna experimenten toe en bepaal per experiment een waarde voor <span class="domain_term">' +
                lc(this.independent) + '</span>. ' +
                'Klik na het invullen van de tabel op <span class="tool_term">Uitvoeren</span>.';
        }
    };

    msg.instructions_run = {
        en: '<p>' +
	    'You will now conduct your experimental runs. ' +
	    'Use the laboratory you see in this screen. ' +
	    'Start with your first experimental run and ' +
	    'enter your observations/findings in the table. ' +
	    'Do this for all your experimental runs. ' +
	    'Once you conducted all your experimental runs ' +
	    'and filled out the table, click <b>Analyse</b>.' +
	    '</p>' +
	    '<p>' +
	    '<em>Instructions laboratory; These instructions are specific ' +
	    'per laboratory and are provided by the owner ' +
	    'of the laboratory that is used.</em>' +
	    '</p>',
        nl: '<p>' +
	    'Je gaat nu je experimenten uitvoeren. ' +
	    'Hiervoor maak je gebruik van het laboratorium ' +
	    'die je in dit scherm ziet. ' +
	    'Voer je eerste experiment uit en geef in de tabel aan ' +
	    'wat je hebt geobserveerd/gemeten. ' +
	    'Doe dit voor al je experimenten. ' + 
	    'Als je al je experimenten hebt gedaan ' +
	    'en de resultaten hebt ingevuld in de tabel, ' +
	    'klik je op <b>Analyseer</b>.' +
	    '</p>' +
	    '<p>' +
	    '<em>Instructies laboratorium; Deze instructies zijn specifiek ' +
	    'per laboratorium en worden gegeven door de eigenaar ' +
	    'van het laboratorium dat gebruikt wordt.</em>' +
	    '</p>'
    };

    msg.same_variable_for_a_role = {
        en: 'You already dropped this variable here.',
        nl: 'Je hebt deze variabele hier al geplaatst.'
    };

    msg.select_at_least_one_vary = {
        en: '<p>Select at least one variable to vary.</p>',
        nl: '<p>Selecteer ten minste &eacute;&eacute;n variabele die je gaat vari&euml;ren.</p>'
    };

    msg.select_exactly_one_measure = {
        en: '<p>Select exactly one variable to observe/measure.</p>',
        nl: '<p>Selecteer precies &eacute;&eacute;n variabele die je gaat observeren/meten.</p>'
    };

    msg.select_all_variables = {
        en: '<p>You have not yet decided for all variables if you want to vary them ' +
            'or keep them the same. ' +
            'To be able to draw sound conclusions, based on comparisons, ' +
            'you must keep all things other than the researched effect the same across ' +
            'experimental runs.<br> ' +
            'Please, decide for each variable if you want to vary it or keep it the same.' +
            '</p>',
        nl: '<p>Je hebt nog niet voor alle variabelen bepaald of je ze wilt vari&euml;ren of ' +
            'hetzelfde wilt houden. ' +
            'Om goede conclusies te kunnen trekken, gebaseerd op vergelijkingen, ' +
            'moet je alles waarvan je het effect niet onderzoekt hetzelfde houden ' +
            'tussen experimenten.<br> ' +
            'Bepaal voor elke variabele of je deze wilt vari&euml;ren of hetzelfde wilt houden.' +
            '</p>'
    };

    msg.drop_expecting_dependent_variable_here = {
        en: function () {
            return '<p>It is not possible to observe/measure <span class="domain_term">' +
                lc(this) + '</span> in the current lab.</p>' +
                '<p>You can only "vary" or "keep the same" <span class="domain_term">'  +
                lc(this) + '</span> ' + 'across experimental runs.</p>'
        },
        nl: function () {
            return '<p>Het is niet mogelijk <span class="domain_term">' +
                lc(this) + '</span> te observeren/meten in het huidige lab.</p>' +
                '<p>Je kunt <span class="domain_term">'  +
                lc(this) + '</span> ' + 'alleen vari&euml;ren of hetzelfde houden tussen experimenten.</p>'
        }
    };

    msg.drop_expecting_independent_variable_here = {
        en: function () {
            return '<p>It is not possible to vary <span class="domain_term">' + lab(this) +
                '</span> in the current lab.</p>' +
                '<p>You can only observe/measure <span class="domain_term">' + lab(this) + '</span>.</p>'
        },
        nl: function () {
            return '<p>Het is niet mogelijk <span class="domain_term">' + lab(this) +
                '</span> te vari&euml;ren in het huidige lab.</p>' +
                '<p>Je kunt <span class="domain_term">' + lab(this) + '</span> alleen observeren/meten.</p>'
        }
    };

    msg.drop_expecting_control_variable_here = {
        en: function () {
            return '<p>It is not possible to keep the same <span class="domain_term">' + lab(this) +
                '</span> in the current lab.</p>' +
                '<p>You can only observe/measure <span class="domain_term">' + lab(this) + '</span>.</p>'
        },
        nl: function () {
            return '<p>Het is niet mogelijk <span class="domain_term">' + lab(this) +
                '</span> hetzelfde te houden in het huidige lab.</p>' +
                '<p>Je kunt <span class="domain_term">' + lab(this) + '</span> alleen observeren/meten.</p>'
        }
    };

/*------------------------------------------------------------
 *  Heuristics
 *------------------------------------------------------------*/

    msg.votat = {
        en: 'If you vary more than one variable at a time, you cannot ' +
            'be sure what causes a possible change in what you observe or measure.' +
            '<br>' +
            'Are you sure you want to vary [TWO] variables?',
        nl: 'Als je meer dan &euml;&euml;n variabele tegelijk varieert, weet je niet ' +
            'zeker wat voor een mogelijke verandering heeft gezorgd in wat je observeert/meet.' +
            '<br>' +
            'Weet je zeker dat je [TWEE] variabelen wilt vari&euml;ren?'
    };

    msg.vary =  {
        en: 'Vary',
        nl: 'Varieer'
    };

    msg.keep_the_same = {
        en: 'Keep the same',
        nl: 'Houd hetzelfde'
    };

    msg.cancel = {
        en: 'Cancel',
        nl: 'Annuleer'
    };

    msg.confirm = {
        en: 'Confirm',
        nl: 'Bevestig'
    };

    msg.ok = {
        en: 'OK',
        nl: 'OK'
    };

    msg.dont_show_again = {
        en: 'Do not show this message again',
        nl: 'Toon dit bericht niet nog een keer'
    };

    msg.warning = {
        en: 'Warning',
        nl: 'Waarschuwing'
    };

    msg.remark = {
        en: 'Remark',
        nl: 'Opmerking'
    };

msg.object_properties = {
    en: 'object properties',
    nl: 'eigenschappen voorwerp'
};

msg.object_measures = {
    en: 'measures',
    nl: 'metingen'
};

msg.experimental_setup = {
    en: 'experimental setup',
    nl: 'experimentele opzet'
};

    msg.vary = {
	en: 'vary',
	nl: 'varieer'
    };

    msg.experiment = {
	en: 'experiment',
	nl: 'experiment'
    };

msg.keep_the_same = {
    en: 'keep the same',
    nl: 'houd hetzelfde'
};

msg.mass = {
    en: 'mass',
    nl: 'massa'
};

msg.material = {
    en: 'material',
    nl: 'materiaal'
};

msg.shape = {
    en: 'shape',
    nl: 'vorm'
};

msg.volume = {
    en: 'volume',
    nl: 'volume'
};

msg.density = {
    en: 'density',
    nl: 'dichtheid'
};

msg.instruments = {
    en: 'instruments',
    nl: 'instrumenten'
};

msg.fluids = {
    en: 'fluids',
    nl: 'vloeistoffen'
};

msg.fluid = {
    en: 'fluid',
    nl: 'vloeistof'
};

msg.fluid_aquarium = {
    en: 'fluid aquarium',
    nl: 'vloeistof aquarium'
};

msg.liquid = {
    en: 'fluid',
    nl: 'vloeistof'
};

msg.observe_measure = {
    en: 'observe/measure',
    nl: 'bekijk/meet'
};

msg.buoyancy = {
    en: 'buoyancy',
    nl: 'opwaartse kracht'
};

msg.sink_or_float = {
    en: 'sink or float ',
    nl: 'zinken of drijven'
};

msg.sinks = {
    en: 'sinks ',
    nl: 'zinkt'
};

msg.floats = {
    en: 'floats ',
    nl: 'drijft'
};

msg.water_displacement = {
    en: 'fluid displacement',
    nl: 'vloeistof verplaatsing'
};

msg.increment = {
    en: 'increment',
    nl: 'stap'
};

msg.add_experimental_row = {
    en: 'Add experimental row',
    nl: 'Voeg experiment toe'
};

msg.drag_here = {
    en: 'Drag here',
    nl: 'Sleep hierheen'
};

    msg.specify = {
	en: 'specify',
	nl: 'bepaal'
    };

    msg.adjust = {
	en: 'adjust',
	nl: 'aanpassen'
    };

    msg.specify_value = {
	en: 'Specify value for',
	nl: 'Bepaal de waarde voor'
    };

    msg.heuristics = {
	en: 'Heuristics',
	nl: 'Vuistregels'
    };

    msg.experiment_design = {
	en: 'Experiment Design',
	nl: 'Experiment Ontwerp'
    };

    msg.plan = {
	en: 'Plan',
	nl: 'Plan'
    };

    msg.design = {
	en: 'Design',
	nl: 'Ontwerp'
    };

    msg.run = {
	en: 'Run',
	nl: 'Uitvoeren'
    };

    msg.lab = {
	en: 'Laboratory',
	nl: 'Laboratorium'
    };

    msg.observed = {
	en: 'observed',
	nl: 'gemeten'
    };

    msg.analyse = {
	en: 'Analyse',
	nl: 'Analyseer'
    };

    msg.design_experiment = {
	en: 'Design experiment',
	nl: 'Ontwerp experiment'
    };

    msg.select_variables = {
	en: 'Select variables',
	nl: 'Selecteer variabelen'
    };

    msg.hypothesis = {
	en: 'Hypothesis',
	nl: 'Hypothese'
    };

    msg.experiment_design_buoyancy = {
	en: 'Experiment Design -- Buoyancy',
	nl: 'Experiment Ontwerp -- Opwaartse kracht'
    };

    msg.experimental_design_tool = {
	en: 'Experimental Design Tool',
	nl: 'Experiment Ontwerp Tool'
    };

    msg.instructions = {
	en: 'Instructions',
	nl: 'Instructies'
    };

    msg.buoyancy_hypothesis = {
	en: '<p>If the density of an object is greater than the density ' +
	    'of the fluid the object will float.</p>',
	nl: '<p>Als de dichtheid van een voorwerp groter is dan de dichtheid ' +
	    'van de vloeistof dan zal het voorwerp drijven.</p>'
    };

    msg.analysis_not_available = {
	en: 'Analysis is currently not available.',
	nl: 'Analyse is op dit moment niet beschikbaar.'
    };

    msg.cm_3 = {
	en: 'cm<sup>3</sub>',
	nl: 'cm<sup>3</sub>'
    };

    msg.sphere = {
	en: 'sphere',
	nl: 'bol'
    };

    msg.cube = {
	en: 'cube',
	nl: 'kubus'
    };

    msg.gram = {
	en: 'gram',
	nl: 'gram'
    };

    msg.and = {
	en: 'and',
	nl: 'en'
    };

    msg.yes_continue = {
	en: 'Yes, continue',
	nl: 'Ja, ga verder'
    };

    msg.no_add_runs = {
	en: 'No, add runs',
	nl: 'Nee, voeg experimenten toe'
    };

    msg['delete'] = {
	en: 'delete',
	nl: 'verwijder'
    };

    msg.switch_language = {
	en: 'You are about to change the language. ' +
	    'If you continue all your changes are lost.',
	nl: 'Je staat op het punt om een andere taal te kiezen. ' +
	    'Als je doorgaat raak je alle veranderingen kwijt.'
    };

/*  msg.allow_switch_design_run = {
	en: 'You are about to finish your experiment design. ' +
	    'Do you think you can test your hypothesis with the ' +
	    'experimental runs you planned?',
	nl: 'Ben je klaar met het experiment ontwerp ' +
	    'en kun je daarmee je hypothese toetsen?'
    };
*/
    msg.allow_switch_run_design_incomplete = {
	en: 'You can only run your experiments when you specified all the values.',
	nl: 'Je kunt de experimenten pas uitvoeren als je alle waarden hebt bepaald.'
    };

    return msg;
})();
