angular
    .module("translateApp")
    .controller("EditMessageController", EditMessageController);


function EditMessageController($scope, $log, $resource) {

    // --------------
    // Initialization
    // --------------


    // --------------
    // Scope-related
    // --------------

    /* SCOPE DATA */

    $scope.messageActive = false;

    $scope.selected = {};

    $scope.values = {
        current: $scope.item.target,
        saved: $scope.item.target, // Value saved into the server
        saving: $scope.item.target // Value being saved
    };

    $scope.status = {};
    $scope.status.saving = false; // Message is being saved (or not)
    $scope.status.error = false; // Error occurred when trying to save.


    /* SCOPE METHODS */

    $scope.confirmTranslation = confirmTranslation;
    $scope.shouldShowFromDefaultWarning = shouldShowFromDefaultWarning;
    $scope.onFocus = onFocus;
    $scope.onChange = onChange;
    $scope.onKey = onKey;
    $scope.isSaved = isSaved;
    $scope.shouldDisplayDetails = shouldDisplayDetails;
    $scope.suggestionSelected = suggestionSelected;
    $scope.onDetailsClose = onDetailsClose;


    /* SCOPE EVENTS */

    // Listen for focus events from our sibling directives.
    $scope.$on("edit-message-focused", onEditMessageFocused);

    $scope.$watch("messageActive", onMessageActive);
    $scope.$watch("item.target", onItemChanged);


    // Just for testing.
    // $scope.$watch("item.target", function(){ $scope.item.format = "textAngular"; $scope.item.can_edit = true; });

    // --------------
    // Implementations
    // --------------

    /**
     * Whether we should show the from-default warning message. We should show it if an item
     * is from_default and at the same time if the message is the original.
     */
    function shouldShowFromDefaultWarning() {
        return $scope.item.from_default && $scope.getCurrentTextValue() == $scope.values.saved;
    } // !shouldShowFromDefaultWarning

    /**
     * To confirm that the current translation is right, and an update should
     * be carried out and from_default removed.
     */
    function confirmTranslation() {

        $log.debug("Confirming translation");

        // Force a save.
        $scope.values.saved = "";
        onChange();

        // Locally change the from_default to indicate that we no longer should show the warning etc.
        // The server should have received the update already, so in a refresh from_default will
        // also be set to false.
        $scope.item.from_default = false;
    } // !confirmTranslation


    /**
     * Listen for item change events. These will happen when other client edits the translation.
     * @param newval
     * @param oldval
     */
    function onItemChanged(newval, oldval) {
        if($scope.values.current != $scope.item.target) {
            $scope.values.current = $scope.item.target;
            $scope.values.saved = $scope.values.current;
            $scope.flashElement();
        }
    } // !onItemChanged


    /**
     * To be called when the messageActive status changes, so that we can focus
     * on the text control if appropriate.
     * @param newval
     * @param oldval
     */
    function onMessageActive(newval, oldval) {
        if(!newval && !oldval)
            return;

        if(newval && !oldval) {
            $scope.focusTextInput();
        }
    } // !onMessageActive

    /**
     * A suggestion was clicked. We should apply it and unfocus the control.
     */
    function suggestionSelected() {
        if($scope.selected == undefined || $scope.selected.suggestion == undefined)
            return;

        $log.debug("Selected suggestion: " + $scope.selected.suggestion.target);

        $scope.values.current = $scope.selected.suggestion.target;
        // The above values.current setting should suffice, but in this case we want it to take effect immediately
        // so that the fake onChange() call can detect it.
        $scope.setCurrentTextValue($scope.selected.suggestion.target);

        // *Disabled for now, because we are meant to focus the next item.
        // $scope.focusTextInput();

        $scope.selected.suggestion = "";

        // Force a save.
        $scope.values.saved = undefined;

        // Trigger a fake onChange event.
        onChange();

        $log.debug("A suggestion was chosen.");

        // Go to the next item; raise a go-next event.
        $log.debug("Emitting edit-go-next event");

        // We keep the messageActive check just in case.
        if($scope.messageActive) {
            $scope.$parent.$emit("edit-go-next", {index: $scope.$parent.index});
        }
    } // !suggestionSelected

    /**
     * Handles an edit-message-focused event, which will often be emmited
     * by our sibling directives. We hide our details page if one of our siblings has the focus.
     */
    function onEditMessageFocused(event, args) {
        var key = args.key;
        var index = args.index;

        if( (key && $scope.key == key) || (index && $scope.$parent.index == index) ) {

            // If we can't edit we do nothing.
            if($scope.item.can_edit) {
                $scope.messageActive = true;
                window.lastScope = $scope;
            }
        }
        else {
            $scope.messageActive = false;
        }
    } // !onEditMessageFocused

    /**
     * True if the form is currently displaying the saved version of the text.
     */
    function isSaved() {
        return $scope.values.saved == $scope.getCurrentTextValue();
    } // !isSaved

    function onFocus(event) {

        $scope.messageActive = true;

        // Inform whoever may be interested (probably our sibling edit-message directives) that we have been
        // selected.
        $scope.$parent.$parent.$broadcast("edit-message-focused", {key: $scope.key});
    } // !onFocus

    function onChange() {
        $log.debug("[EditMessageController/onChange]");
        if (!isSaved()) {
            // We should query a server-side update.

            $scope.status.saving = true;
            $scope.values.saving = $scope.values.current;

            var data = {
                "key": $scope.key,
                "value": $scope.values.saving
            };

            var UpdateMessagePut = $resource(APP_DYN_ROOT + "api/apps/bundles/:language/:target/updateMessage",
            {
                "app_url": $scope.bundle.appurl,
                "language": $scope.bundle.targetlang,
                "target": $scope.bundle.targetgroup
            }, {
                update: {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'
                    }
                }
            });

            var result = UpdateMessagePut.update({}, data);

            result.$promise.then(onUpdateSuccess, onUpdateFailure);
        }

        $scope.unchangedValue = $scope.values.current;
    } // !onChange


    function onUpdateSuccess(result) {
        $scope.status.error = false;
        $scope.status.saving = false;
        $scope.item.from_default = false; // Will no longer be from_default. We guess.
        $scope.values.saved = $scope.values.saving;
    } // !onUpdateSuccess


    function onUpdateFailure(result) {
        $scope.status.error = true;
        $scope.status.saving = false;
    } // !onUpdateFailure


    function shouldDisplayDetails(result) {
        return $scope.messageActive;
    } // !shouldDisplayDetails


    function onKey(event) {
        // 27 = Escape
        if (event.keyCode == 27) {
            $log.debug("Rolling back to " + $scope.unchangedValue);
            this.getModelController().$rollbackViewValue();
        }

        if (event.keyCode == 13) {
            $log.debug("Enter detected. Skipping to next item");

            // Go to the next item; raise a go-next event.
            $log.debug("Emitting edit-go-next event");

            // We keep the messageActive check just in case.
            if($scope.messageActive) {
                $scope.$parent.$emit("edit-go-next", {index: $scope.$parent.index});
            }
        }
    } // !onKey

    function onDetailsClose() {
        $scope.messageActive = false;
    } // !onDetailsClose

} // !EditMessageController
