// Original code developed by University of Twente, taken and adapted from:
// http://go-lab.gw.utwente.nl/sources/tools/conceptmap/src/main/webapp/coffee/ConfigDialog0.1.js
//
// TODO: This needs some clean-up and refactoring.

(function () {
    "use strict";
    window.ut = window.ut || {};

    window.ut.tools = window.ut.tools || {};

    window.ut.tools.conceptmapper = window.ut.tools.conceptmapper || {};

    window.ut.tools.conceptmapper.ConfigDialog = (function () {
        function ConfigDialog(appName, currentConfiguration, configurationCallback) {
            var $dialogElement, $fieldset, $form,
                _this = this;
            $dialogElement = $(document.body).find("#ut_tools_conceptmapper_ConfigDialog");
            $dialogElement.append("<h3>{{ gettext('Application options') }}</h3>");
            $form = $("<form class='form-horizontal' role='form'></form>");

            $.each(currentConfiguration, function (id, setting) {
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

            $form.submit(function () {
                event.preventDefault();
            });

            $dialogElement.append($form);

            // Listen for changes in the forms so that we know when to activate the auto-save feature.
            $form.find("input").change(function(ev){
                console.log("CHANGE: " + ev);
                onChangeOccurred();
            });
            $form.find("input[type=text]").bind("input propertychange", function(ev) {
                console.log("TCHANGE: " + ev);
                onChangeOccurred();
            });

            // To display the saving state.

            // TextBox on the end:
            //var $status = $('<input type="text" class="form-control" readonly/>');

            // Alert box on the top, fixed pos:
            var $status = $('<div class="alert alert-dismissible alert-success" role="alert" style="position: fixed; top: 5%; left: 5%; width: 90%; opacity: 0.9;"/>');
            $status.hide();
            $("body").append($status);


            // Shows and changes the status.
            function status(s, fade) {
                var cur = $status.text();
                if(cur !== s) {
                    $status.fadeIn(300);
                    $status.text(s);

                    if(fade)
                        $status.delay(1000).fadeOut(1000);
                }
            }

            //status("Saving changes...", false);


            function onChangeOccurred() {
                status("Saving changes...", false);
                window.last_change = new Date();
            }

            // Every second, consider saving if we need to and we have not saved lately.
            var considerSaving = function() {
                // If we have never saved we need to save straightaway. This could actually be done
                // on server-side initialization only, but for now this is the easiest.
                if(window.last_save == undefined)
                {
                    if(window.saving == undefined || window.saving.state() == "resolved")
                        window.saving = doSave();
                }

                // If there have been no changes at all, we do nothing.
                else if(window.last_change == undefined)
                {
                }

                // If there have been changes we check whether we should save now.
                // Only if we are not already saving, though.
                else if(window.saving == undefined || window.saving.state() === "resolved")
                {
                    var now = new Date();
                    var between_saves = window.last_save.getTime() - window.last_change.getTime();
                    var since_last_save = now.getTime() - window.last_save.getTime();

                    // If more than 3 seconds have elapsed since the last save, and if there are changes at all, then we save.
                    if(between_saves <= 0 && since_last_save > 3000) {
                        if(window.saving == undefined || window.saving.state() === "resolved")
                            window.saving = doSave();
                    }
                } //!else


                // We program ourselves to try again in a second.
                setTimeout(considerSaving, 500);
            };

            // Save for the firs time and start the save-loop.
            considerSaving();

            function extractConfiguration() {
                $.each(currentConfiguration, function (id, settings) {
                    if (settings.type === "boolean") {
                        $form.find("input[name='" + id + "']").each(function (index, input) {
                            return currentConfiguration["" + id].value = $(input).is(':checked').toString();
                        });
                    }
                    if (settings.type === "array") {
                        $form.find("input[name='" + id + "']").each(function (index, input) {
                            return currentConfiguration["" + id].value = $(input).val().split(",");
                        });
                    }
                    if (settings.type === "string") {
                        return $form.find("input[name='" + id + "']").each(function (index, input) {
                            return currentConfiguration["" + id].value = $(input).val();
                        });
                    }
                });
            }

            function doSave() {
                console.log("Saving...");
                status("Saving changes...", false);

                var promise = $.Deferred();
                extractConfiguration();

                // Save without reloading the page.
                configurationCallback({ 'appName': appName, 'config': currentConfiguration }, false)
                    .done(function(){
                        // Store the date of the last successful save
                        window.last_save = new Date();
                        status("All changes saved", true);
                        promise.resolve();
                    })
                    .fail(function(){
                        promise.reject();
                    });

                return promise.promise();
            }

        };

        return ConfigDialog;

    })();

    var keys = [];
    for (var k in window.golab.tools.configurationDefinition) keys.push(k);
    var appName = keys[0];
    var config = window.golab.tools.configurationDefinition[appName];

    new window.ut.tools.conceptmapper.ConfigDialog(appName, config, golabConfigurationSavedCallback);
}).call(this);

/*
 //@ sourceMappingURL=ConfigDialog0.1.map
 */
