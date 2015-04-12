angular
    .module("translateApp")
    .controller("ChangeSourceController", ChangeSourceController);


function ChangeSourceController($scope, $modalInstance) {

    //--------------
    // Scope-related
    //--------------

    /* SCOPE ATTRIBUTES */

    $scope.selected = {};


    /* SCOPE METHODS */
    $scope.cancel = cancel;
    $scope.ok = ok;


    /* SCOPE WATCHES */

    // Initialize the default value when it is ready.
    $scope.$watch("appinfo.translations", function (newval, oldval) {
        if (newval != undefined)
            $scope.selected.lang = "all_ALL";
    });

    // Handle the selected event for the Lang field.
    $scope.$watch("selected.lang", onLangSelected);

    // Handle the selected event for the Target field.
    $scope.$watch("selected.target", onTargetSelected);




    // ---------------
    // Implementations
    // ---------------

    function onLangSelected(newval, oldval) {
        if (newval == undefined)
            return;

        $scope.selected.lang_info = $scope.appinfo.translations[$scope.selected.lang];

        $scope.selected.target = "ALL";
        onTargetSelected();
    } // !onLangSelected

    function onTargetSelected(newval, oldval) {
        if (newval == undefined)
            return;

        $scope.selected.target_info = $scope.selected.lang_info.targets[$scope.selected.target];
    } // !onTargetSelected

    function cancel() {
        $modalInstance.dismiss('cancel');
    } // !cancel

    function ok() {
        $modalInstance.close($scope.selected);
    } // !ok

} // !ChangeSourceController