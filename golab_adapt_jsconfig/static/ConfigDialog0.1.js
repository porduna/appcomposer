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
      $fieldset = $("<fieldset/>");
      $.each(currentConfiguration, function(id, setting) {
        $input;
        var $input;
        if (setting.type === "boolean") {
          $input = $("<input type='checkbox' name='" + id + "'> " + setting.label + "</input>");
          if (setting.value === "true") {
            $input.attr("checked", "checked");
          }
          $fieldset.append($input);
        } else if (setting.type === "array" || setting.type === "string") {
          $input = $("<input type='text' name='" + id + "'></input>");
          $input.val(setting.value);
          $fieldset.append("<label for='" + id + "'>" + setting.label + "</label>");
          $fieldset.append($input);
        } else {
          $input = $("<input type='text' name='" + id + "'></input>");
          $fieldset.append("<label for='" + id + "'>" + setting.label + "</label>");
          $fieldset.append($input);
        }
        $input.attr("title", "" + setting.description + ".");
        if (setting.configurable === "false") {
          $input.attr("readonly", true);
        }
        return $fieldset.append("<br/>");
      });
      $form = $("<form/>");
      $form.append($fieldset);
      $form.submit(function() { event.preventDefault(); });
      $dialogElement.append($form);
      var $saveBtn = $("<button class='btn'>Save</button>");
      $saveBtn.click(function() {
            $.each(currentConfiguration, function(id, settings) {
              if (settings.type === "boolean") {
                $fieldset.find("input[name='" + id + "']").each(function(index, input) {
                  return currentConfiguration["" + id].value = $(input).is(':checked').toString();
                });
              }
              if (settings.type === "array") {
                $fieldset.find("input[name='" + id + "']").each(function(index, input) {
                  return currentConfiguration["" + id].value = $(input).val().split(",");
                });
              }
              if (settings.type === "string") {
                return $fieldset.find("input[name='" + id + "']").each(function(index, input) {
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
