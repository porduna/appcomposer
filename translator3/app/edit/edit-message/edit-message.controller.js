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

    // To keep track of the original value while a value is being modified, so that we can rollback.
    $scope.unchangedValue = $scope.item.target;


    $scope.onChange = onChange;
    $scope.onKey = onKey;


    // --------------
    // Implementations
    // --------------

    function onChange() {
        $log.debug("[EditMessageController/onChange]");

        if ($scope.unchangedValue != $scope.currentValue) {
            // We should query a server-side update.

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

            var result = UpdateMessagePut.update(data, data);
        }

        $scope.unchangedValue = $scope.currentValue;
    } // !onChange


    function onKey(event) {
        if (event.keyCode == 27) {
            $log.debug("Rolling back to " + $scope.unchangedValue);

            // Rollback the change. Simply changing the currentValue in the scope is *not* enough.
            $scope.currentValue = $scope.unchangedValue;
            event.target.value = $scope.currentValue;
            event.target.blur();
        }
    } // !onKey


} // !EditMessageController