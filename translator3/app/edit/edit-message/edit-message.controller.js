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

    $scope.currentValue = $scope.item.target;
    $scope.savedValue = $scope.item.target; // Value saved into the server
    $scope.savingValue = $scope.item.target; // Value being saved

    $scope.status = {};
    $scope.status.saving = false; // Message is being saved (or not)
    $scope.status.error = false; // Error occurred when trying to save.


    $scope.onFocus = onFocus;
    $scope.onChange = onChange;
    $scope.onKey = onKey;
    $scope.isSaved = isSaved;


    // --------------
    // Implementations
    // --------------

    /**
     * True if the form is currently displaying the saved version of the text.
     */
    function isSaved() {
        return $scope.savedValue == $scope.getCurrentTextValue();
    } // !isSaved

    function onFocus() {
    } // !onFocus

    function onChange() {
        $log.debug("[EditMessageController/onChange]");

        if (!isSaved) {
            // We should query a server-side update.

            $scope.status.saving = true;
            $scope.savingValue = $scope.currentValue;

            var data = {
                key: $scope.key,
                value: $scope.value
            };

            var UpdateMessagePut = $resource(APP_DYN_ROOT + "api/bundle/updateMessage/:appurl/:targetlang/:targetgroup",
            {
                "appurl": $scope.bundle.appurl,
                "targetlang": $scope.bundle.targetlang,
                "targetgroup": $scope.bundle.targetgroup
            }, {
                update: {
                    method: 'PUT'
                }
            });

            var result = UpdateMessagePut.update({}, data);

            result.$promise.then(onUpdateSuccess, onUpdateFailure);
        }

        $scope.unchangedValue = $scope.currentValue;
    } // !onChange


    function onUpdateSuccess(result) {
        $scope.status.error = false;
        $scope.status.saving = false;
        $scope.savedValue = $scope.savingValue;
    } // !onUpdateSuccess


    function onUpdateFailure(result) {
        $scope.status.error = true;
        $scope.status.saving = false;
    } // !onUpdateFailure


    function onKey(event) {
        if (event.keyCode == 27) {
            $log.debug("Rolling back to " + $scope.unchangedValue);

            this.getModelController().$rollbackViewValue();
        }
    } // !onKey


} // !EditMessageController