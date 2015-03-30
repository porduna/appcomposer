angular
    .module("translateApp")
    .controller("AppController", AppController);


function AppController($scope, $routeParams, $resource) {

    //////////////////
    // Initialization
    //////////////////

    var controller = this;
    var Appinfo = $resource(APP_DYN_ROOT + "api/apps/:appurl");

    //////////////////
    // Scope-related
    //////////////////

    $scope.params = $routeParams;
    $scope.appurl = $routeParams.appurl;
    $scope.appinfo = Appinfo.get({appurl: $scope.appurl});

    $scope.test = test;


    //////////////////
    // Implementations
    //////////////////

    function test() {
        debugger;
    }

} //! AppController


