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

    $scope.currentValue = $scope.item.target;
    $scope.savedValue = $scope.item.target; // Value saved into the server
    $scope.savingValue = $scope.item.target; // Value being saved

    $scope.status = {};
    $scope.status.saving = false; // Message is being saved (or not)
    $scope.status.error = false; // Error occurred when trying to save.


    /* SCOPE METHODS */

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

    // --------------
    // Implementations
    // --------------


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

        $scope.currentValue = $scope.selected.suggestion.target;
        // The above currentValue setting should suffice, but in this case we want it to take effect immediately
        // so that the fake onChange() call can detect it.
        $scope.setCurrentTextValue($scope.selected.suggestion.target);

        // *Disabled for now, because we are meant to focus the next item.
        // $scope.focusTextInput();

        $scope.selected.suggestion = "";

        // Trigger a fake onChange event.
        onChange();
    } // !suggestionSelected

    /**
     * Handles an edit-message-focused event, which will often be emmited
     * by our sibling directives. We hide our details page if one of our siblings has the focus.
     */
    function onEditMessageFocused(event, args) {
        $log.debug("[onEditMessageFocused]");

        var key = args.key;
        var index = args.index;

        $log.debug("Index: " + index);

        if( (key && $scope.key == key) || (index && $scope.$parent.index == index) ) {
            $scope.messageActive = true;
            $log.debug("Message active to True");

            $log.debug("WE SHOULD SELECT: " + $scope.key + " " + index);
            window.lastScope = $scope;
        }
        else {
            $log.debug("Message active to False");
            $scope.messageActive = false;
        }
    } // !onEditMessageFocused

    /**
     * True if the form is currently displaying the saved version of the text.
     */
    function isSaved() {
        return $scope.savedValue == $scope.getCurrentTextValue();
    } // !isSaved

    function onFocus(event) {

        event.preventDefault();

        $scope.messageActive = true;

        // Inform whoever may be interested (probably our sibling edit-message directives) that we have been
        // selected.
        $scope.$parent.$parent.$broadcast("edit-message-focused", {key: $scope.key});
    } // !onFocus

    function onChange() {
        $log.debug("[EditMessageController/onChange]");
        if (!isSaved()) {
            // We should query a server-side update.

            // Go to the next item; raise a go-next event.
            $log.debug("Emitting edit-go-next event");

            // If we are saving and apparently we remain the active message, we are done here, so
            // We want to automatically skip to the next.
            if($scope.messageActive) {
                $scope.$parent.$emit("edit-go-next", {index: $scope.$parent.index});
            }

            $scope.status.saving = true;
            $scope.savingValue = $scope.currentValue;

            var data = {
                "key": $scope.key,
                "value": $scope.savingValue
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

            var result = UpdateMessagePut.update(data, {});

            result.$promise.then(onUpdateSuccess, onUpdateFailure);
        }

        $scope.unchangedValue = $scope.currentValue;
    } // !onChange


    function onUpdateSuccess(result) {
        $scope.status.error = false;
        $scope.status.saving = false;
        $scope.item.from_default = false; // Will no longer be from_default. We guess.
        $scope.savedValue = $scope.savingValue;
    } // !onUpdateSuccess


    function onUpdateFailure(result) {
        $scope.status.error = true;
        $scope.status.saving = false;
    } // !onUpdateFailure


    function shouldDisplayDetails(result) {
        return $scope.messageActive;
    } // !shouldDisplayDetails


    function onKey(event) {
        if (event.keyCode == 27) {
            $log.debug("Rolling back to " + $scope.unchangedValue);

            this.getModelController().$rollbackViewValue();
        }
    } // !onKey

    function onDetailsClose() {
        $scope.messageActive = false;
    } // !onDetailsClose

} // !EditMessageController