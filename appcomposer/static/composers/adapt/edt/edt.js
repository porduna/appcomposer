/*  $Id$	-*- mode: javascript -*-
 *  
 *  File	edt.js
 *  Part of	Go-Lab Experimental Design Tool
 *  Author	Anjo Anjewierden, a.a.anjewierden@utwente.nl
 *  Purpose	Overall class
 *  Works with	JavaScript
 *  
 *  Notice	Copyright (c) 2013  University of Twente
 *  
 *  History	21/03/13  (Created)
 *  		10/06/13  (Last modified)
 */

/*------------------------------------------------------------
 *  Directives
 *------------------------------------------------------------*/
/*  Use with gcc -E -x c -P -C *.h > *.js 
 */

var edt = new function() {
    var that = this;

    this.messages = []; // See messages.js

    var mode = null; // 'plan', 'design', 'run', ...

    var language = 'en'; // Normally change using url: ?lang=

    var confirm_flags = {
 drop: {
     independent: true,
     dependent: true,
     control: true
 },
 multiple: {
     independent: true,
     dependent: true,
     control: true
 }
    };

    function set_confirm_flags(bool) {
 confirm_flags.drop.independent = bool;
 confirm_flags.drop.dependent = bool;
 confirm_flags.drop.control = bool;
 confirm_flags.multiple.independent = bool;
 confirm_flags.multiple.dependent = bool;
 confirm_flags.multiple.control = bool;
    };

    var bg_drop = false;

    function dialog(id, title, html) {
 $(id).html(html);
 $(id).dialog({ title: title,
         width: 500,
         buttons: {
      "OK": function() {
          $(this).dialog('close');
      }
         }
       });
    }

    // Translate silently (no warning when translation not found)
    // Used for units like '... gram'.
    function trs(what, atts) {
 var struct = that.messages[what];

 if (struct && struct[language])
     return translate(what, atts);
 return what;
    };

    function translate(msg, atts, lang0) {
 var lang = lang0 || language;
 var struct = that.messages[msg];

 if (!(lang && struct && struct[lang])) {
     console.log('*** Warning: no translation for "' + msg + '" in ' + lang);
     return msg;
 }

 struct = struct[lang];

 if (atts) {
     if (typeof(struct) === 'function')
  return struct.call(atts);
     console.log('*** Warning: message for "' + msg + '" not a function ');
     return msg;
 }
 return struct;
    };

    function uuid() {
 var i;
        var c = "89ab";
        var u = [];
        for (i = 0; i < 36; i += 1) {
            u[i] = (Math.random() * 16 | 0).toString(16);
        }
        u[8] = u[13] = u[18] = u[23] = "-";
        u[14] = "4";
        u[19] = c.charAt(Math.random() * 4 | 0);
        return u.join("");
    };

    var domain = null;
    var experiment = null;

    var context = {
 design_table: null,
 experiment_specification: null
    };

    function name_object_list(names, array) {
 var list = [];

 for (var name, i=0; i<names.length, name=names[i]; i++) {
     if (array[name])
  list.push({name: name, object: array[name]});
     else
  console.log('*** Warning: name ' + name + ' not found in ' + array);
 }

 return list;
    };

    function extend(sub_class, super_class) {
 var F = function() {};

 F.prototype = super_class.prototype;
 sub_class.prototype = new F();
 sub_class.prototype.constructor = sub_class;

 sub_class.superclass = super_class.prototype;
 if (super_class.prototype.constructor == Object.prototype.constructor)
     super_class.prototype.constructor = super_class;
    }

    //  Move obj to list.  If list2 is given obj should be removed from it.
 function confirm_drop(list, obj, list2) {
     var role = list.role();

     if (confirm_flags.drop[role] === false) {
  list.append(obj);
  if (list2)
      list2.remove(obj);
  return;
     }

     var id = '#edt_dialog_warning';
     var txt;

     switch (role) {
     case 'independent':
  txt = translate('confirm_drop_independent', obj);
  break;
     case 'dependent':
  txt = translate('confirm_drop_dependent', obj);
  break;
     case 'control':
  txt = translate('confirm_drop_control', obj);
  break;
     default:
  txt = 'Unknown role ' + role + ' in confirm_drop()';
     }

     $(id).html('<p>' + txt + '</p>' +
         '<input id="edt_dont_show_again" type="checkbox"> ' +
         translate('dont_show_again'));
     $("#edt_dont_show_again").click(function () {
  confirm_flags.drop[role] = false;
     });
     $(id).dialog(
  { title: translate('confirm'),
    dialogClass: 'no-close',
    width: 500,
    modal: true,
    buttons: {
        "OK": function() {
     $(this).dialog('close');
     list.append(obj);
/*			  if (list2) {
			      list2.remove(obj);

			  }
*/ },
        "Cancel": function() {
     $(this).dialog('close');
        }
    }
  });
 }

    /*------------------------------------------------------------
     *  class Base -- id, name, dom
     *------------------------------------------------------------*/

    var Base = this.Base = function(atts) {
 this._id = atts.id || uuid();
 this._name = atts.name || this._id;
 this._class_name = atts.class_name || this._id;
 this._dom = null;
 if (atts.parent)
     this._parent = atts.parent;

 return this;
    }

    Base.prototype.id = function() { return this._id; };
    Base.prototype.name = function(v0) { if (v0 === undefined) return this._name; this._name = v0; return this; };
    Base.prototype.class_name = function(v0) { if (v0 === undefined) return this._class_name; this._class_name = v0; return this; };
    Base.prototype.parent = function(v0) { if (v0 === undefined) return this._parent; this._parent = v0; return this; };

    /** Return the printable label of an object.  Takes into account the language
	defined and capitalizes by default.
     */
    Base.prototype.label = function(lc) {
 var lab = translate(this._name);

 return (lc ? lab : lab.capitalize());
    }

    /** Associate receiver with a corresponding DOM object and vice versa.  The
	optional container is the object representing the enclosing HTML element.
     */
    Base.prototype.dom = function(jqref, container) {
 if (jqref === undefined)
     return this._dom;

 jqref[0].edt_object = this;
 if (container)
     jqref[0].edt_container = container;
 this._dom = jqref;

 return this;
    }

    Base.prototype.debug = function() {
 console.log('debug ' + this);
 for (p in this) {
     if (typeof(this[p]) === 'function')
  continue;
     console.log('  ' + p + ' ' + typeof(this[p]) + ' ' + this[p]);
 }
    }


    /*------------------------------------------------------------
     *  Class PropertyValue -- no longer used
     *------------------------------------------------------------*/

    var PropertyValue = this.PropertyValue = function(atts) {
 Base.call(this, atts);

 this._magnitude = atts.magnitude || null;
 this._unit = atts.unit || null;
 this._value = atts.value || null;

 return this;
    }

    extend(PropertyValue, Base);

    PropertyValue.prototype.magnitude = function() { return this._magnitude; };
    PropertyValue.prototype.unit = function() { return this._unit; };
    PropertyValue.prototype.value = function() { return this._value; };

    PropertyValue.prototype.toString = function() {
 return 'PropertyValue(' + this.name() + ')';
    }

    PropertyValue.prototype.json = function(hdr) {
 var props = { name: this.name(),
         magnitude: this.magnitude(),
         unit: this.unit(),
         value: this.value()
      };
 if (hdr)
     return { property_value: props };
 return props;
    }

    function plan_experiment() {
 var all_props = experiment.object_property_selection_table();
 var all_measures = experiment.object_measure_selection_table();

 mode = 'plan';

 $('#edt_div_plan_selection')
     .empty()
     .append(all_props.dom())
     .append(all_measures.dom());
 $('#edt_div_plan_experiment')
     .append(context.design_table.dom());
 $('#edt_content_instructions')
     .html(translate('instructions_plan'));
 $('#edt_container_hypothesis').show();
 $('#edt_content_hypothesis')
     .html(translate('buoyancy_hypothesis'));
 $('#edt_container_heuristics').show();
 $('#edt_content_heuristics')
     .html(translate('heuristics_plan'));
 $("#edt_container_lab").hide();

 return true;
    };

    function allow_plan_experiment() {
 return true;
    };

    /** Check the plan for the current experiment and give feedback when
	necessary.  Returns true when the drop is consistent, and the
	top-level should ask for confirmation.  If false is returned, either
	the modification is made in this function, or not allowed.
     */
    function allow_drop_plan_experiment(list, obj) {
 var tab = context.design_table;
 var i_list = tab.independent_list();
 var c_list = tab.control_list();
 var d_list = tab.dependent_list();
 var i_vars = i_list.variables();
 var c_vars = c_list.variables();
 var d_vars = d_list.variables();
 var warning = translate('warning');
 var remark = translate('remark');
 var id = '#edt_dialog_warning';
 var vary = translate('vary').capitalize() + ': ';
 var keep = translate('keep_the_same').capitalize() + ': ';
 var cancel = translate('cancel');
 var ok = translate('ok');
 var dont_show_again = translate('dont_show_again');
 var dont_show = '<input id="edt_dont_show_again" type="checkbox"> ';
 var i, j;

 //  We are not in the background
 bg_drop = false;

 //  Variable is dropped on the list it is in
 if (obj instanceof Variable && obj.parent && obj.parent() === list)
     return false;

 //  Variable is dropped more than once on a list
 if (!(obj instanceof Variable)) {
     if (list.member(obj)) {
  dialog(id, warning,
         translate('same_variable_for_a_role'));
  return false;
     }
 }

 //  More than one independent variable
 if (list === i_list && i_vars.length > 0) {
     var vars = [obj].concat(i_vars);

     var buttons = {};

     if (vars.length === 2) {
  var lab1 = vars[0].label();
  var lab2 = vars[1].label();
  var txt = translate('multiple_independent_variables',
        { vars: vars,
          conjunction: translate('and')
        });

  buttons[vary + lab1] =
      function() {
   $(this).dialog("close");
   i_list.remove(var2);
   i_list.append(obj);
      };
  buttons[vary + lab2] =
      function() {
   $(this).dialog("close");
      };
  buttons[vary + lab1 + ' & ' + lab2] =
      function() {
   $(this).dialog("close");
   i_list.append(obj);
      };
  buttons[cancel] =
      function() {
   $(this).dialog("close");
      };
  // Then ask desired location
  $(id).html(txt);
  $(id).dialog(
      { title: warning,
        width: 500,
        dialogClass: 'no-close',
        modal: true,
        buttons: buttons
      });
     } else {
  var txt = translate('too_many_independent_variables',
        { vars: vars });

  $(id).html(txt);
  $(id).dialog(
      { title: warning,
        width: 500,
        dialogClass: 'no-close',
        modal: true,
        buttons: {
     "OK":
     function() {
         $(this).dialog("close");
     }
        }
      });
     }

     return false;
 }

 //  More than one control variable
 if (list === c_list && c_vars.length > 0 && confirm_flags.multiple.control) {
     dialog(id, remark,
         '<p>' + translate('multiple_control_variables') + '</p>' +
        dont_show + dont_show_again);
     $("#edt_dont_show_again").click(function () {
  confirm_flags.multiple.control = false;
     });

     list.append(obj);
     return false;
 }

 //  Moving from one list to another
 if (obj instanceof Variable) {
     if (list === i_list && c_list.member(obj)) {
  confirm_drop(list, obj, c_list);
  return false;
     }
     if (list === c_list && i_list.member(obj)) {
  confirm_drop(list, obj, i_list);
  return false;
     }
 }

 //  Variable is both independent and control
 if ((list === i_list && c_list.member(obj)) ||
     (list === c_list && i_list.member(obj))) {
     var lab = obj.label();
     var txt = translate('multiple_roles_for_a_variable', obj);
     var buttons = {};
     var list2 = null;

     if (obj instanceof Variable)
  list2 = obj.parent();

     buttons[vary + lab] =
  function() {
      $(this).dialog("close");
      c_list.remove(obj);
      i_list.append(obj);
      if (list2)
   list2.remove(obj);
  };
     buttons[keep + lab] =
  function() {
      $(this).dialog("close");
      i_list.remove(obj);
      c_list.append(obj);
      if (list2)
   list2.remove(obj);
  };
     buttons[cancel] =
  function() {
      $(this).dialog("close");
  };

     $(id).html(txt);
     $(id).dialog(
  { title: warning,
    width: 500,
    dialogClass: 'no-close',
    modal: true,
    buttons: buttons
  });

     return false;
 }

 return true;
    }

    /** Check the plan for the current experiment and give feedback when
	necessary.  Returns true when the plan is complete, false otherwise.
     */
    function allow_design_experiment() {
 var tab = context.design_table;
 var i_vars = tab.variables('independent');
 var c_vars = tab.variables('control');
 var d_vars = tab.variables('dependent');
 var warning = translate('warning');
 var id = '#edt_dialog_warning';
 var i, j;

 if (i_vars.length < 1) {
     dialog(id, warning,
     translate('select_at_least_one_vary'));
     return false;
 }

 if (d_vars.length !== 1) {
     dialog(id, warning,
         translate('select_exactly_one_measure'));
     return false;
 }

 var props = experiment.object_property_selection();
 var all_vars = i_vars.concat(c_vars);

 for (var prop, i=0; i<props.length, prop=props[i]; i++) {
     var seen = false;
     for (var cv, j=0; j<all_vars.length, cv=all_vars[j]; j++) {
  if (prop === cv.name()) {
      seen = true;
      break;
  }
     }
     if (!seen) {
  dialog(id, warning,
      translate('select_all_variables'));
  return false;
     }
 }

 for (i=0; i<i_vars.length; i++) {
     for (j=0; j<c_vars.length; j++) {
  if (i_vars[i] === c_vars[j]) {
      dialog('#edt_dialog_warning', hdr,
          translate('multiple_roles_for_a_variable'));
      return false;
  }
     }
 }

 return true;
    }

    function design_experiment() {
 var tab = context.design_table;
 var i_vars = tab.variables('independent');
 var c_vars = tab.variables('control');
 var d_vars = tab.variables('dependent');
 var vars = [];
 var es = context.experiment_specification;

 mode = 'design';

 for (var nth, i=0; i<i_vars.length, nth=i_vars[i]; i++)
     vars.push(nth.copy());
 for (var nth, i=0; i<c_vars.length, nth=c_vars[i]; i++)
     vars.push(nth.copy());
 for (var sp, i=0; i<experiment.system_property_selection().length, sp=experiment.system_property_selection()[i]; i++)
     vars.push(new Variable(
  { role: 'system',
    domain_concept: domain.system_property(sp),
    name: domain.system_property(sp).name()
  }));

 for (var nth, i=0; i<d_vars.length, nth=d_vars[i]; i++)
     vars.push(nth.copy());

 var atts =
     { variables: vars,
       experiment: experiment
     };

 if (es && !es.compatible(atts)) {
     dialog('#edt_dialog_warning',
         translate('warning'),
         translate('plan_modifications_incompatible'));
     es = null;
 }

 if (!es) {
     es = new ExperimentSpecification(atts);
 }

 context.experiment_specification = es;

 $("#edt_div_design_experiment").html(es.dom());
 es.repaint();

 $('#edt_content_instructions')
     .html(translate('instructions_design',
    { independent: i_vars[0],
      control: c_vars[0],
      dependent: d_vars[0],
      domain: domain
    }));
 $('#edt_container_hypothesis').show();
 $('#edt_container_heuristics').show();
 $("#edt_container_lab").hide();
 $('#edt_content_heuristics')
     .html(translate('heuristics_design'));

 return true;
    }

    function allow_analyse_experiment() {
 dialog('#edt_dialog_warning',
     translate('remark'),
     translate('analysis_not_available')
     );
 return false;
    }

    function allow_run_experiment() {
 var es = context.experiment_specification;
 var id = '#edt_dialog_warning';

 if (es.completely_specified())
     return true;
 dialog(id, translate('warning'),
        translate('allow_switch_run_design_incomplete'));
 return false;

/**/ var id = '#edt_dialog_warning';
 var cont = translate('yes_continue');
 var add_runs = translate('no_add_runs');

 var buttons = {};
 buttons[cont] = function() {
     $("#edt_tabs").tabs({ active: 2,
      disabled: []
    });
     run_experiment();
     $(id).dialog('close');
 };
 buttons[add_runs] = function() {
     $("#edt_tabs").tabs({ active: 1,
      disabled: []
    });
     design_experiment();
     $(id).dialog('close');
 };

 $(id).html('<p>' + translate('allow_switch_design_run') + '</p>');
 $(id).dialog(
     { title: translate('confirm'),
       dialogClose: 'no-close',
       width: 500,
       modal: true,
       buttons: buttons
     });

 return true;
/**/ }

    function analyse_experiment() {
 alert('Analyse experiment not implemented');
    }

    function run_experiment() {
 var es = context.experiment_specification;

 mode = 'run';
 es.repaint();
 $("#edt_div_run_experiment").html(es.dom());

 $('#edt_content_instructions')
     .html(translate('instructions_run'));
 $('#edt_container_heuristics').hide();
 $('#edt_container_hypothesis').hide();
 $("#edt_container_lab").show();
    }

    function load_language(lang) {
 var parts = document.location.href.split('?');

 document.location.href = parts[0] + '?lang=' + lang;
    }

    function parse_language() {
 var parts = document.location.search.match(/\?lang=(..)/);

 if (parts)
     return parts[1];
 return null;
    }

    /*------------------------------------------------------------
     *  Start EDT
     *------------------------------------------------------------*/

    this.start = function(atts) {
 language = parse_language() || 'en';

 if (atts.domain)
     domain = new Domain(atts.domain);
 if (atts.experiment)
     experiment = new Experiment(atts.experiment);
 if (atts.confirm_flags)
     set_confirm_flags(atts.confirm_flags);
 if (!context.design_table)
     context.design_table = new ExperimentalDesignTable({});

 function confirm_language(newlang) {
     var id = '#edt_dialog_warning';

     if (newlang === language)
  return;

     $(id).html('<p>' + translate('switch_language') + '</p>');
     $(id).dialog(
  { title: translate('warning'),
    dialogClose: 'no-close',
    width: 500,
    modal: true,
    buttons: {
        "OK": function() {
     $(this).dialog('close');
     switch_language(newlang);
        },
        "Cancel": function() {
     $(this).dialog('close');
        }
    }
  }
     );
 }

 function switch_language(newlang) {
     load_language(newlang);
     var parts = document.location.href.split('?');
     document.location.href = parts[0] + '?lang=' + newlang;
 }

 $("#edt_button_language_nl").click(function () {
     confirm_language('nl');
 });

 $("#edt_button_language_en").click(function () {
     confirm_language('en');
 });

 $("#edt_tabs").tabs({ active: 0,
         disabled: [2],
         beforeActivate: function(event, ui) {
      if ($(ui.newTab).hasClass('edt_button_plan')) {
          return allow_plan_experiment();
      }
      if ($(ui.newTab).hasClass('edt_button_design')) {
          return allow_design_experiment();
      }
      if ($(ui.newTab).hasClass('edt_button_run')) {
          return allow_run_experiment();
      }
      if ($(ui.newTab).hasClass('edt_button_analyse')) {
          return allow_analyse_experiment();
      }
      return false;
         },
         activate: function(event, ui) {
      if ($(ui.newTab).hasClass('edt_button_plan')) {
          $("#edt_tabs")
       .tabs('option', 'disabled', [2]);
          plan_experiment();
          return;
      }
      if ($(ui.newTab).hasClass('edt_button_design')) {
          $("#edt_tabs")
       .tabs('option', 'disabled', []);
          design_experiment();
          return;
      }
      if ($(ui.newTab).hasClass('edt_button_run')) {
          $("#edt_tabs")
       .tabs('option', 'disabled', [1]);
          run_experiment();
          return;
      }
      if ($(ui.newTab).hasClass('edt_button_analyse')) {
          $("#edt_tabs")
       .tabs('option', 'disabled', []);
          analyse_experiment();
          return;
      }
         }
       }),

 $(".edt_translate")
     .each(function() {
  $(this).text(translate($(this).text()));
     });

 plan_experiment();
    }


    /*------------------------------------------------------------
     *  Lists of variables
     *------------------------------------------------------------*/

    this.VariableList = function(atts) {
 Base.call(this, atts);

 this._variables = atts.variables || [];
 this._role = atts.role || null;
 this._editable = (atts.editable === undefined ? true : atts.editable);
 this._orientation = atts.orientation || 'vertical';
 this._instance_of = atts.instance_of;
 this._instance_error_message = atts.instance_error_message;

 var html = '<table id="' + this.id() + '" class="' + this.class_name() + '">';
 var dom = $(html);
 var me = this;

 this.dom(dom);
 this.repaint();

 return this;
    }

    var VariableList = this.VariableList;

    extend(VariableList, Base);

    VariableList.prototype.variables = function() { return this._variables; };
    VariableList.prototype.editable = function() { return this._editable; };
    VariableList.prototype.role = function() { return this._role; };
    VariableList.prototype.orientation = function() { return this._orientation; };

    this.VariableList.prototype.toString = function() {
 return 'VariableList(' + this._role + ')';
    }

    this.VariableList.prototype.repaint = function() {
 var tab = this;
 var dom = tab.dom();

 dom.html('');
 dom.append('<tr><th class="edt_th_variable_list">' + tab.label() + '</th></tr></table>');

 for (var value, i=0; i<tab._variables.length, value=tab._variables[i]; i++) {
     if (value._cancelled) {
  tab.remove(value);
  return this;
     }
 }

 for (var value, i=0; i<tab._variables.length, value=tab._variables[i]; i++) {
     tab.display(value);
 }

 dom.append('<tr><td class="edt_td_empty_variable_list"><em>'
     + translate('drag_here')
     + '</em></td></tr>');

 if (this._editable) {
     dom.droppable( {
  drop: function(ev, ui) {
      var obj = ui.draggable[0].edt_object;

      if (obj instanceof tab._instance_of ||
   (obj.domain_concept &&
    obj.domain_concept() instanceof tab._instance_of)) {
   var drop_status = allow_drop_plan_experiment(tab, obj);

   if (drop_status === true) {
       if (!tab.member(obj))
    confirm_drop(tab, obj);
       return;
   }
      } else {
   dialog('#edt_dialog_warning',
       translate('warning'),
       translate(tab._instance_error_message, obj));
   if (obj instanceof Variable) {
       bg_drop = false;
   }
      }
  }
     });
 }

 return this;
    }

    this.VariableList.prototype.append = function(value, force) {
 var is_member = this.member(value);

 if (!force && is_member)
     return this;

 if (!is_member) {
     if (!(value instanceof Variable))
  value = new Variable(
      { domain_concept: value,
        role: this.role(),
        name: value.name(),
        experiment: experiment,
        parent: this
      });
     else {
  //  Remove from previous parent
  if (value.parent() instanceof VariableList) {
      value.parent().remove(value);
  }
  value.role(this.role());
  value.parent(this);
     }
     this._variables.push(value);
     this.repaint();
 }
 return this;
    }

    this.VariableList.prototype.display = function(entry) {
 var options = { draggable: true };

 if (entry.value())
     options.show_value = true;

 var dom = entry.html(options);
 var me = this;

 dom.draggable({
     cursor: 'move',
     helper: 'clone',
     start: function(ev, ui) {
  bg_drop = true;
     },
     stop: function(ev, ui) {
  if (bg_drop === true)
      me.remove(entry);
//		entry._dragged_from = me;
//		
     }
 });

 if (this._orientation === 'vertical')
     $(this._dom).append($('<tr>').append(dom));
 else
     $(this._dom).append(dom);

 return this;
    }

    this.VariableList.prototype.domain_concept = function(v1, v2) {
 if (v1 instanceof DomainConcept)
     return v1;
 if (v1 instanceof Variable)
     return v1.domain_concept();

 return null;
    }

    this.VariableList.prototype.member = function(value) {
 var dc = this.domain_concept(value);

 for (var cv, i=0; i<this._variables.length, cv=this._variables[i]; i++)
     if (cv.domain_concept() === dc)
  return true;
 return false;
    }

    this.VariableList.prototype.remove = function(value) {
 var dc = this.domain_concept(value);

 for (var cv, i=0; i<this._variables.length, cv=this._variables[i]; i++) {
     if (cv.domain_concept() === dc) {
  this._variables.splice(i, 1);
  this.repaint();
  break;
     }
 }
    }

    this.VariableList.prototype.pp = function() {
 console.log('VariableList ' + this._name);
 for (var i=0; i<this._variables.length; i++) {
     console.log('  [' + i + '] ' + this._variables[i]);
 }
    }


    /*------------------------------------------------------------
     *  Class Domain
     *------------------------------------------------------------*/

    var Domain = this.Domain = function(atts) {
 Base.call(this, atts);

 this._description = atts.description || {};
 this._object_properties = [];
 this._object_relations = [];
 this._object_measures = [];
 this._system_properties = [];

 for (var vals, i=0; i<atts.object_properties.length, vals=atts.object_properties[i]; i++) {
     var obj = new ObjectProperty(vals);
     this._object_properties[obj.name()] = obj;
 }

 for (var vals, i=0; i<atts.object_relations.length, vals=atts.object_relations[i]; i++) {
     var obj = new ObjectRelation(vals);
     this._object_relations[obj.name()] = obj;
 }

 for (var vals, i=0; i<atts.object_measures.length, vals=atts.object_measures[i]; i++) {
     var obj = new ObjectMeasure(vals);
     this._object_measures[obj.name()] = obj;
 }

 for (var vals, i=0; i<atts.system_properties.length, vals=atts.system_properties[i]; i++) {
     var obj = new SystemProperty(vals);
     this._system_properties[obj.name()] = obj;
 }

 return this;
    }

    extend(Domain, Base);

    Domain.prototype.name = function() { return this._name; };
    Domain.prototype.description = function() { return this._description; };
    Domain.prototype.object_properties = function() { return this._object_properties; };
    Domain.prototype.object_relations = function() { return this._object_relations; };
    Domain.prototype.object_measures = function() { return this._object_measures; };
    Domain.prototype.system_properties = function() { return this._system_properties; };

    this.Domain.prototype.system_property = function(name) {
 return this._system_properties[name] || null;
    }

    this.Domain.prototype.json = function(caption) {
 var atts = { name: this.name(),
       description: this.description(),
       object_properties: this.object_properties(),
       object_relations: this.object_relations(),
       object_measures: this.object_measures(),
       system_properties: this.system_properties()
     };

 return (caption ? { domain: atts} : atts);
    }


    /*------------------------------------------------------------
     *  DomainConcept
     *------------------------------------------------------------*/

    var DomainConcept = this.DomainConcept = function(atts) {
 Base.call(this, atts);

 return this;
    }

    extend(DomainConcept, Base);


    /*------------------------------------------------------------
     *  Class Property
     *------------------------------------------------------------*/

    var Property = this.Property = function(atts) {
 DomainConcept.call(this, atts);

 this._type = atts.type || 'quantity';
 this._symbol = atts.symbol || null;
 this._unit = atts.unit || null;
 this._values = atts.values || null;

 return this;
    }

    extend(Property, DomainConcept);

    Property.prototype.type = function() { return this._type; };
    Property.prototype.symbol = function() { return this._symbol; };
    Property.prototype.unit = function() { return this._unit; };
    Property.prototype.values = function() { return this._values; };

    this.Property.prototype.toString = function() {
 return 'Property: ' + this.name();
    }

    this.Property.prototype.json = function(caption) {
 var atts = { name: this.name(),
       type: this.type(),
       symbol: this.symbol(),
       unit: this.unit(),
       values: this.values()
     };

 return (caption ? { property: atts } : atts);
    }

    /*------------------------------------------------------------
     *  Class ObjectProperty
     *------------------------------------------------------------*/

    var ObjectProperty = this.ObjectProperty = function(atts) {
 Property.call(this, atts);
    }

    extend(ObjectProperty, Property);

    ObjectProperty.prototype.toString = function() {
 return 'ObjectProperty(' + this.name() + ')';
    }


    /*------------------------------------------------------------
     *  Class ObjectRelation
     *------------------------------------------------------------*/

    var ObjectRelation = this.ObjectRelation = function(atts) {
 DomainConcept.call(this, atts);
    }

    extend(ObjectRelation, DomainConcept);

    ObjectRelation.prototype.toString = function() {
 return 'ObjectRelation(' + this.name() + ')';
    }


    /*------------------------------------------------------------
     *  Class Measure
     *------------------------------------------------------------*/

    var Measure = this.Measure = function(atts) {
 DomainConcept.call(this, atts);
    }

    extend(Measure, DomainConcept);

    Measure.prototype.toString = function() {
 return 'Measure(' + this.name() + ')';
    }

    /*------------------------------------------------------------
     *  Class ObjectMeasure
     *------------------------------------------------------------*/

    var ObjectMeasure = this.ObjectMeasure = function(atts) {
 Measure.call(this, atts);
    }

    extend(ObjectMeasure, Measure);

    ObjectMeasure.prototype.toString = function() {
 return 'ObjectMeasure(' + this.name() + ')';
    }

    /*------------------------------------------------------------
     *  Class SystemProperty
     *------------------------------------------------------------*/

    var SystemProperty = this.SystemProperty = function(atts) {
 Property.call(this, atts);
    }

    extend(SystemProperty, Property);

    SystemProperty.prototype.toString = function() {
 return 'SystemProperty(' + this.name() + ')';
    }


    /*------------------------------------------------------------
     *  Class Experiment
     *------------------------------------------------------------*/

    var Experiment = this.Experiment = function(atts) {
 Base.call(this, atts);

 this._domain = domain;
 this._object_property_selection = atts.object_property_selection;
 this._object_measure_selection = atts.object_measure_selection;
 this._object_property_specification = atts.object_property_specification;
 this._system_property_selection = atts.system_property_selection;
 this._system_property_values = atts.system_property_values;

 return this;
    }

    extend(Experiment, Base);

    Experiment.prototype.domain = function() { return this._domain; };
    Experiment.prototype.object_property_selection = function() { return this._object_property_selection; };
    Experiment.prototype.object_measure_selection = function() { return this._object_measure_selection; };
    Experiment.prototype.object_property_specification = function() { return this._object_property_specification; };
    Experiment.prototype.system_property_selection = function() { return this._system_property_selection; };
    Experiment.prototype.system_property_values = function() { return this._system_property_values; };

    this.Experiment.prototype.toString = function() {
 return 'Experiment(' + this.name() + ')';
    }

    this.Experiment.prototype.object_property_selection_table = function() {
 var names = this._object_property_selection;
 var dops = domain.object_properties();
 var entries = name_object_list(names, dops);

 return new NameObjectList( {
     id: 'edt_object_property_selection',
     name: 'object_properties',
     entries: entries,
     editable: false
 });
    }

    this.Experiment.prototype.object_measure_selection_table = function() {
 var names = this._object_measure_selection;
 var dms = domain.object_measures();
 var entries = name_object_list(names, dms);

 return new NameObjectList( {
     id: 'edt_object_measure_selection',
     name: 'object_measures',
     entries: entries,
     editable: false
 });
    }

    this.Experiment.prototype.system_property_value = function(name) {
 for (var p, i=0; i<this._system_property_values.length, p=this._system_property_values[i]; i++)
     if (p.property === name)
  return p.value;
 return null;
    }

    this.Experiment.prototype.object_property_specification = function(name) {
 var props = this._object_property_specification;

 for (var i=0; i<props.length; i++)
     if (props[i].property === name)
  return props[i];
 return null;
    }


    /*------------------------------------------------------------
     *  Variables with roles
     *------------------------------------------------------------*/

    var Variable = this.Variable = function(atts) {
 Base.call(this, atts);
 this._domain_concept = atts.domain_concept;
 this._role = atts.role;
 this._value = atts.value || null;
 this._experiment = atts.experiment || experiment;
 this._parent = atts.parent || null;

 return this;
    }

    extend(Variable, Base);

    Variable.prototype.domain_concept = function(v0) { if (v0 === undefined) return this._domain_concept; this._domain_concept = v0; return this; };
    Variable.prototype.role = function(v0) { if (v0 === undefined) return this._role; this._role = v0; return this; };
    Variable.prototype.value = function(v0) { if (v0 === undefined) return this._value; this._value = v0; return this; };
    Variable.prototype.experiment = function(v0) { if (v0 === undefined) return this._experiment; this._experiment = v0; return this; };
    Variable.prototype.parent = function(v0) { if (v0 === undefined) return this._parent; this._parent = v0; return this; };

    this.Variable.prototype.toString = function() {
 return 'Variable(' + this.name() + ')';
    }

    this.Variable.prototype.copy = function() {
 return new Variable(
     { name: this.name(),
       class_name: this.class_name(),
       domain_concept: this._domain_concept,
       role: this._role,
       value: this._value,
       experiment: this._experiment,
       parent: null
     });
    }

    this.Variable.prototype.html = function(options) {
 var show_value = (options.show_value === undefined ? false : options.show_value);
 var show_label = (options.show_value === undefined ? true : options.show_label);
 var editable = (options.editable === undefined ? false : options.editable);
 var show_drag = (options.show_drag === undefined ? false : options.show_drag);
 var inactive = (options.inactive === undefined ? false : options.inactive);
 var str;

 str = '<td class="edt_td_variable_list ';
 if (inactive)
     str += 'edt_td_variable_inactive';
 str += '">';
 str += '<div>';
 if (editable) {
     str += '<span class="edt_edit_me">\u25BC&nbsp;&nbsp;</span>';
 }
 if (show_drag)
     str += '\u00AB';
 if (show_label)
     str += this.label();
 if (show_drag)
     str += '\u00BB';
 if (show_label && show_value)
     str += ': ';
 if (show_value) {
     if (this.domain_concept() instanceof ObjectProperty) {
  var spec = experiment.object_property_specification(this.name());

  str += (this.value() === null ? '?' : trs(this.value()));
  if (spec.unit)
      str += ' ' + translate(spec.unit);
     } else {
  str += (this.value() === null ? '?' : this.value());
     }
 }
 str += '</div></td>';

 var dom = $(str);
 var me = this;
 if (editable)
     dom.click(function() { me.specify_value(); });
 this.dom(dom);

 return dom;
    }


    /** Specify a value for a variable.
     *
     *  Creates a dialog in which the user can enter a value based on the
     *  specification of the domain concept in the experiment description.
     *
     *  Returns false when the value has not been set, true otherwise.
     */
    this.Variable.prototype.specify_value = function(options0) {
 var options = options0 || {};
 var dc = this.domain_concept();
 var exp = experiment;
 var id = '#edt_dialog_specify_value';
 var me = this;
 var repaint = options.repaint || me.parent();

 $(id).empty();

 if (dc instanceof ObjectProperty) {
     var spec = exp.object_property_specification(dc.name());

     $(id).empty();

     if (spec.range) {
  var unit = (spec.unit ? ' ' + translate(spec.unit) : '');
  var old_value = this.value();
  var value = (old_value === null ? spec.initial : old_value);
  var minimum = spec.range.minimum;
  var maximum = spec.range.maximum;
  var increment = spec.range.increment || 0;
  var label = this.label();
  var id_input = 'edt_input_specify_value';
  var id_slider = 'edt_slider_specify_value';
  var str = '<p>' + label + ' <span id="' + id_input + '">' +
      '<b>' + value + '</b>' + '</span> ' + unit + '</p>' +
      '<div id="' + id_slider + '"></div>';
  $(id).html(str);
  $("#" + id_slider).slider(
      { value: value,
        min: minimum,
        max: maximum,
        step: increment,
        slide: function( event, ui ) { // <b> should be style TBD
     $("#" + id_input).html('<b>' + ui.value + '</b>');
     me.value(ui.value);
        }
      });
  $("#" + id_input).val($("#" + id_slider).slider("value"));

  me.value(value);
  options.cancel_value = old_value;
  show_dialog(id, options, me);

  return this;
     }

     if (spec.values) { // TBD only two values
  var str = '<div id="edt_div_specify_values">';

  for (var i=0; i<spec.values.length; i++) {
      var r_val = spec.values[i];
      var r_lab = translate(spec.values[i]).capitalize();
      var r_id = 'range' + i;
      str += '<input type="radio" id="' + r_id + '" value="' + r_val + '"/>';
      str += '<label for="' + r_id + '">' + r_lab + '</label>';
  }
  str += '</div';
  $(id).html(str);

      // TBD - other values

  $("#range0").click(function() {
      var c_val = $('#range0').attr('value');
      me.value(c_val);
  });
  $("#range1").click(function() {
      var c_val = $('#range1').attr('value');
      me.value(c_val);
  });
  $("#edt_div_specify_values").buttonset();

  show_dialog(id, options, me);

  return this;
     }
 }

 if (dc instanceof ObjectMeasure && dc.name() === 'sink_or_float') {
     var spec = { values: ['sinks', 'floats'] };
     var str = '<div id="edt_div_specify_values">';

     for (var i=0; i<spec.values.length; i++) {
  var r_val = spec.values[i];
  var r_lab = translate(spec.values[i]).capitalize();
  var r_id = 'range' + i;
  str += '<input type="radio" id="' + r_id + '" value="' + r_val + '"/>';
  str += '<label for="' + r_id + '">' + r_lab + '</label>';
     }
     str += '</div';
     $(id).html(str);

     // TBD - other values

     $("#range0").click(function() {
  var c_val = $('#range0').attr('value');
  me.value(c_val);
     });
     $("#range1").click(function() {
  var c_val = $('#range1').attr('value');
  me.value(c_val);
     });
     $("#edt_div_specify_values").buttonset();

     show_dialog(id, options, me);

     return this;
 }

 alert('Sorry, this measurement is currently not supported');

 return false;

 function show_dialog(id, options, me) {
     var buttons = {};

     buttons.OK = function() {
  $(this).dialog("close");
  if (repaint && repaint.repaint)
      repaint.repaint();
     }

     if (options.cancel_option !== false)
  buttons.Cancel = function() {
      $(this).dialog("close");
      me._cancelled = true;
      if (options.cancel_value)
   me.value(options.cancel_value);
      if (repaint && repaint.repaint)
   repaint.repaint();
  };

     $(id).dialog(
  { title: translate('specify_value') + ': ' + trs(me.name()),
    width: 500,
    dialogClass: 'no-close',
    modal: true,
    buttons: buttons
  });
 }
    }

    /*------------------------------------------------------------
     *  Class ExperimentSpecification
     *------------------------------------------------------------*/

    var ExperimentSpecification = this.ExperimentSpecification = function(atts) {
 var me = this;

 Base.call(this, atts);

 this._variables = atts.variables;
 this._experiment = atts.experiment || experiment;
 this._header = new ExperimentRunHeader(
     { variables: this._variables,
       parent: this
     });
 this._specify = new ExperimentRunSpecify(
     { variables: this._variables,
       parent: this
     });
 this._last_run = 0;
 this._runs = [];

 // Set default values of system properties
 for (var v, i=0; i<this._variables.length, v=this._variables[i]; i++) {
     if (v.role() === 'system') {
  var val = this._experiment.system_property_value(v.name());
  if (val === null)
      console.log('*** Warning: No value for system property ' + v.name());
  v.value(val);
     }
 }

 var dom = $('<table class="edt_table_experiment_specification"></table>');
 this.dom(dom);

 $("#edt_button_add_experimental_row").button(
     { icons: { primary: 'ui-icon-plusthick' },
       label: translate('add_experimental_row')
     });

 $("#edt_button_add_experimental_row").click(function() {
     me.add_run();
     me.repaint();
 });

 dom.append(this._header.dom());
 dom.append(this._specify.dom());

 this.add_run();

 return this;
    }

    extend(ExperimentSpecification, Base);

    ExperimentSpecification.prototype.runs = function(v0) { if (v0 === undefined) return this._runs; this._runs = v0; return this; };
    ExperimentSpecification.prototype.variables = function(v0) { if (v0 === undefined) return this._variables; this._variables = v0; return this; };

    this.ExperimentSpecification.prototype.toString = function() {
 return 'ExperimentSpecification()';
    }

    this.ExperimentSpecification.prototype.repaint = function() {
 var dom = this.dom();

 dom.empty();
 dom.append(this._header.dom().empty());
 dom.append(this._specify.dom().empty());
 this.fill_dom();

 return this;
    }

    this.ExperimentSpecification.prototype.completely_specified = function() {
 for (var run, i=0; i<this._runs.length, run=this._runs[i]; i++) {
     if (run.completely_specified())
  continue;
     return false
 }
 return true;
    }

    this.ExperimentSpecification.prototype.compatible = function(atts) {
 if (this._experiment !== atts.experiment)
     return false;

 var vars = atts.variables;

 if (this._variables.length !== vars.length)
     return false;

 for (var v, i=0; i<vars.length, v=vars[i]; i++) {
     var compat = false;
     for (var v2, j=0; j<this._variables.length, v2=this._variables[j]; j++) {
  if (v.domain_concept() === v2.domain_concept()) {
      if (v.role() === v2.role()) {
   compat = true;
   break;
      }
  }
     }
     if (compat === false)
  return false;
 }
 return true;
    }

    this.ExperimentSpecification.prototype.fill_dom = function() {
 var dom = this.dom();

 this._header.fill_dom();
 if (mode === 'design')
     this._specify.fill_dom();
 for (var run, i=0; i<this.runs().length, run=this.runs()[i]; i++) {
     dom.append(run.dom());
     run.repaint();
 }

 return this;
    }

    this.ExperimentSpecification.prototype.add_run = function() {
 var run = new ExperimentRun({ variables: this.variables(),
          parent: this,
          nth: ++this._last_run
        });
 this.runs().push(run);

 return this;
    }

    this.ExperimentSpecification.prototype.remove = function(r) {
 for (var run, i=0; i<this._runs.length, run=this._runs[i]; i++) {
     if (run === r) {
  this._runs.splice(i, 1);
  this.repaint();
  break;
     }
 }
 return this;
    }


    /*------------------------------------------------------------
     *  Class ExperimentRunHeader
     *------------------------------------------------------------*/

    var ExperimentRunHeader = this.ExperimentRunHeader = function(atts) {
 Base.call(this, atts);
 this._variables = atts.variables; // Point to same array

 var dom = $('<tr class="edt_tr_experiment_header"></tr>');
 this.dom(dom);

 return this;
    }

    extend(ExperimentRunHeader, Base);

    this.ExperimentRunHeader.prototype.toString = function() {
 return 'ExperimentRunHeader()';
    }

    this.ExperimentRunHeader.prototype.repaint = function() {
 this.dom().empty();
 return this.fill_dom();
    }

    this.ExperimentRunHeader.prototype.fill_dom = function() {
 var dom = this.dom();

 dom.append('<th class="edt_th_experiment_nth">' +
     translate('experiment').capitalize() + '</th>');
 for (var v, i=0; i<this._variables.length, v=this._variables[i]; i++) {
     var name = v.domain_concept().name();
     var cn = 'edt_th_experiment_variable edt_td_role_' + v.role();

     dom.append('<th class="' + cn + '">' + v.label() + '</th>');
 }

 if (mode === 'design')
     dom.append('<th class="edt_th_experiment_variable"></th>'); // Delete button

 return this;
    }


    /*------------------------------------------------------------
     *  Class ExperimentRunSpecify
     *------------------------------------------------------------*/

    var ExperimentRunSpecify = this.ExperimentRunSpecify = function(atts) {
 Base.call(this, atts);
 this._variables = atts.variables; // Point to same array

 var dom = $('<tr class="edt_tr_experiment_specify"></tr>');
 this.dom(dom);
    }

    extend(ExperimentRunSpecify, Base);

    this.ExperimentRunSpecify.prototype.toString = function() {
 return 'ExperimentRunSpecify()';
    }

    this.ExperimentRunSpecify.prototype.repaint = function() {
 this.dom().empty();
 return this.fill_dom();
    }

    this.ExperimentRunSpecify.prototype.fill_dom = function() {
 var dom = this.dom();
 var spec = this.parent();

 dom.append('<td></td>'); // Experiment column

 for (var v, i=0; i<this._variables.length, v=this._variables[i]; i++) {
     // Only control needs to be specified
     if (v.role() !== 'control') {
  dom.append('<td></td>');
  continue;
     }

     var id = 'edt_specify_' + v.name();

     dom.append('<td class="edt_td_experiment_specify">' +
         '<button id="' + id + '"></button></td>' );
     $('#'+id).button(
  { icons: { primary: 'ui-icon-circle-arrow-s' },
    label: (v.value() === null
     ? translate('specify').capitalize()
     : translate('adjust').capitalize())
  });

     $('#'+id).click((function(v) {
  return function() { v.specify_value({repaint: spec});
      };
     })(v));
 }

 if (mode === 'design')
     dom.append('<td></td>'); // Delete column
    }

    var ExperimentRun = this.ExperimentRun = function(atts) {
 Base.call(this, atts);
 this._experiment = atts.experiment || experiment;
 this._variables = [];
 this._nth = (atts.nth === undefined ? '*' : atts.nth);

 var dom = $('<tr class="edt_tr_experiment_run" id="' + this.id() + '"></tr>');
 this.dom(dom);

 for (var ith, i=0; i<atts.variables.length, ith=atts.variables[i]; i++) {
     var v = ((ith.role() === 'independent') || (ith.role() === 'dependent')
       ? ith.copy() : ith);

     v.parent(this);
     this._variables.push(v);
 }

 this.repaint();

 return this;
    }

    extend(ExperimentRun, Base);

    ExperimentRun.prototype.variables = function(v0) { if (v0 === undefined) return this._variables; this._variables = v0; return this; };
    ExperimentRun.prototype.nth = function() { return this._nth; };
    ExperimentRun.prototype.experiment = function() { return this._experiment; };

    this.ExperimentRun.prototype.toString = function() {
 return 'ExperimentRun()';
    }

    this.ExperimentRun.prototype.completely_specified = function() {
 for (var v, i=0; i<this._variables.length, v=this._variables[i]; i++) {
     if (v.role() === 'dependent' || (v.value() !== null))
  continue;
     return false;
 }
 return true;
    }

    this.ExperimentRun.prototype.repaint = function () {
 var dom = this.dom();
 var spec = this.parent();
 var me = this;

 dom.empty();
 dom.append('<td class="edt_td_experiment_nth">' +
//		   (mode === 'run' ? 'RUN ' : '') +
     this._nth + '</td>');

 for (var v, i=0; i<this._variables.length, v=this._variables[i]; i++) {
     if (v.role() === 'dependent' && mode === 'run') {
  if (!v.value()) {
      var id = 'edt_specify_' + v.name() + '_' + this.nth();

      dom.append('<td class="edt_td_experiment_specify">' +
          '<button id="' + id + '"></button></td>' );
      $('#'+id).button(
   { icons: { primary: 'ui-icon-circle-arrow-s' },
     label: translate('observed').capitalize()
   });

      $('#'+id).click((function(v) {
   return function() {
       v.specify_value({repaint: spec});
   };
      })(v));
  } else {
      dom.append(v.html({ show_value: true,
     show_label: false,
     editable: true
          }));
  }
  continue;
     }

     if (v.value() !== null) { // TBD -- make given independent editable
  if (v.role() === 'independent') {
      dom.append(v.html({ show_value: true,
     show_label: false,
     editable: true
          }));
  } else {
      dom.append(v.html({ show_value: true,
     show_label: false
          }));
  }
  continue;
     }

     if (v.role() === 'independent') {
  var id = 'edt_specify_' + v.name() + '_' + this.nth();

  dom.append('<td class="edt_td_experiment_specify">' +
      '<button id="' + id + '"></button></td>' );
  $('#'+id).button(
      { icons: { primary: 'ui-icon-circle-arrow-s' },
        label: translate('specify').capitalize()
      });

  $('#'+id).click((function(v) {
      return function() { v.specify_value({repaint: spec});
          };
  })(v));
  continue;
     }

     if (v.role() === 'dependent') {
  dom.append(v.html({ show_value: true,
        show_label: false,
        inactive: true
      }));
  continue;
     }

     dom.append(v.html({ show_value: true,
    show_label: false
         }));
 }

 if (mode === 'design') {
     var id = 'edt_button_run_delete' + this.nth();
     var str = '<td class="edt_button_delete_run">' +
  '<div><button id="' + id + '"></button></div></td>';

     dom.append(str);
     $("#"+id).button(
  { icons: { primary: 'ui-icon-trash' },
    label: translate('delete').capitalize()
  });

     $("#"+id).click(function() {
  spec.remove(me);
     });
 }

 return this;
    }


    /*------------------------------------------------------------
     *  Class ExperimentalDesignTable
     *------------------------------------------------------------*/

    var ExperimentalDesignTable = this.ExperimentalDesignTable = function(atts) {
 Base.call(this, atts);

 this._class_name = 'edt_table_experimental_design';
 this._independent_list = new VariableList({
     id: 'edt_independent_variables',
     name: 'vary',
     role: 'independent',
     instance_of: Property,
     instance_error_message: 'drop_expecting_independent_variable_here',
     class_name: 'edt_table_variable_list',
     variables: atts.independent_variables || [],
     parent: this
 });
 this._control_list = new VariableList({
     id: 'edt_control_variables',
     name: 'keep_the_same',
     role: 'control',
     instance_of: Property,
     instance_error_message: 'drop_expecting_control_variable_here',
     class_name: 'edt_table_variable_list',
     variables: atts.control_variables || [],
     parent: this
 });
 this._dependent_list = new VariableList({
     id: 'edt_dependent_variables',
     name: 'observe_measure',
     role: 'dependent',
     instance_of: Measure,
     instance_error_message: 'drop_expecting_dependent_variable_here',
     class_name: 'edt_table_variable_list',
     variables: atts.dependent_variables || [],
     parent: this
 });

 var dom = $('<table id="' + this.id() + '" class="' + this.class_name() + '">' +
      '<tr></tr></table>').append('<td>', this._independent_list.dom(), '</td>',
      '<td>', this._control_list.dom(), '</td>',
      '<td>', this._dependent_list.dom(), '</td>');

 this.dom(dom);

 return this;
    }

    extend(ExperimentalDesignTable, Base);

    ExperimentalDesignTable.prototype.control_list = function() { return this._control_list; };
    ExperimentalDesignTable.prototype.independent_list = function() { return this._independent_list; };
    ExperimentalDesignTable.prototype.dependent_list = function() { return this._dependent_list; };

    this.ExperimentalDesignTable.prototype.variables = function(type) {
 switch (type) {
 case 'dependent':
     return this._dependent_list.variables();
 case 'control':
     return this._control_list.variables();
 case 'independent':
     return this._independent_list.variables();
 default:
     console.log('*** Warning: .variables type is not one of dependent, control or independent');
     return [];
 }
    }


    /*------------------------------------------------------------
     *  Lists of name / object pairs
     *------------------------------------------------------------*/

    var NameObjectList = this.NameObjectList = function(atts) {
 Base.call(this, atts);

 this._class_name = atts.class_name || 'edt_table_variable_list';
 this._orientation = atts.orientation || 'vertical';
 this._entries = []; // Filled with .append

 var html =
     '<table id="' + this.id() + '" class="' + this.class_name() + '">' +
     '<tr><th colspan="5" class="edt_table_header">' + this.label() +
     '</th></tr></table>';
 var dom = $(html);

 this.dom(dom); // Must be before .append
 for (var i=0; i<atts.entries.length; i++)
     this.append(atts.entries[i]);

 return this;
    }

    extend(NameObjectList, Base);

    NameObjectList.prototype.values = function() { return this._values; };
    NameObjectList.prototype.orientation = function() { return this._orientation; };
    NameObjectList.prototype.entries = function() { return this._entries; };

    this.NameObjectList.prototype.append = function(entry) {
 var name = entry.name;
 var object = entry.object;

 this._entries[name] = object;

 var div = '<div>\u00AB ' + object.label() + ' \u00BB</div>';
 var dom = $('<td id="' + name + '" class="edt_td_name_object_list"></td>')
     .append(div);
 object.dom(dom, this);

 dom.draggable({
     cursor: 'move',
            helper: 'clone'
//	    helper: function () { return $(div); }
 });

 if (this._orientation === 'vertical')
     $(this._dom).append($('<tr>').append(dom));
 else
     $(this._dom).append(dom);
    }

    return this;
}();
