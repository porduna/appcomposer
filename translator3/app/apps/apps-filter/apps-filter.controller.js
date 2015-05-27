angular
    .module("translateApp")
    .controller("AppsFilterController", AppsFilterController);


function AppsFilterController($scope) {

    // ---------------
    // Scope
    // ---------------

    $scope.filterEnabled = false;

    $scope.toggleFilter = toggleFilter;

    // ---------------
    // Implementations
    // ---------------

    function toggleFilter() {
        $scope.filterEnabled = !$scope.filterEnabled;
    } // !toggleFilter


} // !AppsFilterController