angular
    .module("translateApp")
    .controller("AppCtrl", AppCtrl);


function AppCtrl($scope, $routeParams, $position) {
    $scope.params = $routeParams
}