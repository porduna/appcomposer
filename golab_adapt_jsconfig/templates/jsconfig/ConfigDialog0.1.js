// Original code developed by University of Twente, taken and adapted from:
// http://go-lab.gw.utwente.nl/sources/tools/conceptmap/src/main/webapp/coffee/ConfigDialog0.1.js

(function() {
  "use strict";
  window.ut = window.ut || {};

  window.ut.tools = window.ut.tools || {};

  window.ut.tools.conceptmapper = window.ut.tools.conceptmapper || {};

  window.ut.tools.conceptmapper.ConfigDialog = (function() {
    function ConfigDialog(appName, currentConfiguration, configurationCallback) {
      var $dialogElement, $fieldset, $form,
        _this = this;
      $dialogElement = $(document.body).find("#ut_tools_conceptmapper_ConfigDialog");
      $form = $("<form class='form-horizontal' role='form'/>");

      $.each(currentConfiguration, function(id, setting) {
        var $current_line = $("<div class='form-group'></div>");

        var $input;
        if (setting.type === "boolean") {
          var $current_container = $("<div class='col-sm-offset-2 col-sm-10'><div class='checkbox'><label></label></div></div>");
          $input = $("<input type='checkbox' name='" + id + "'> " + setting.label + "</input>");
          $current_container.find("label").append($input);

          if (setting.description) {
            $current_container.append("<span class='help-block''>" + setting.description + "</span>");
          }
          if (setting.value === "true") {
            $input.attr("checked", "checked");
          }
          $current_line.append($current_container);
        } else if (setting.type === "array" || setting.type === "string") {
          var $current_label = $("<label for='" + id + "' class='col-sm-2 control-label'>" + setting.label + "</label>");
          var $current_container = $("<div class='col-sm-10'></div>");
          $input = $("<input type='text' name='" + id + "' size='50'></input>");
          $input.val(setting.value);
          $current_container.append($input);
          $current_line.append($current_label);
          if (setting.description) {
            $current_container.append("<span class='help-block''>" + setting.description + "</span>");
          }

          $current_line.append($current_container);
        } else {
          var $current_label = $("<label for='" + id + "' class='col-sm-2 control-label'>" + setting.label + "</label>");
          var $current_container = $("<div class='col-sm-10'></div>");
          $input = $("<input type='text' name='" + id + "'></input>");
          $input.val(setting.value);
          $current_container.append($input);
          $current_line.append($current_label);
          if (setting.description) {
            $current_container.append("<span class='help-block''>" + setting.description + "</span>");
          }

          $current_line.append($current_container);
        }
        $input.attr("title", "" + setting.description + ".");
        if (setting.configurable === "false") {
          $input.attr("readonly", true);
        }
        $form.append($current_line);
      });
      $form.submit(function() { event.preventDefault(); });
      $dialogElement.append($form);
      var $saveBtn = $("<button class='btn'>{{ gettext("Save") }}</button>");
      $saveBtn.click(function() {
            $.each(currentConfiguration, function(id, settings) {
              if (settings.type === "boolean") {
                $form.find("input[name='" + id + "']").each(function(index, input) {
                  return currentConfiguration["" + id].value = $(input).is(':checked').toString();
                });
              }
              if (settings.type === "array") {
                $form.find("input[name='" + id + "']").each(function(index, input) {
                  return currentConfiguration["" + id].value = $(input).val().split(",");
                });
              }
              if (settings.type === "string") {
                return $form.find("input[name='" + id + "']").each(function(index, input) {
                  return currentConfiguration["" + id].value = $(input).val();
                });
              }
            });
            configurationCallback({ 'appName' : appName, 'config' : currentConfiguration });
          });
      $dialogElement.append($saveBtn);
    };

    return ConfigDialog;

  })();

  var keys = [];
  for(var k in window.golab.tools.configurationDefinition) keys.push(k);
  var appName = keys[0];
  var config = window.golab.tools.configurationDefinition[appName];
  
  new window.ut.tools.conceptmapper.ConfigDialog(appName, config, golabConfigurationSavedCallback);
}).call(this);

/*
//@ sourceMappingURL=ConfigDialog0.1.map
*/
