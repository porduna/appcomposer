angular
    .module("translateApp")
    .controller("AppController", AppController);


function AppController($scope, $routeParams, $resource, $log) {

    // ---------------------------
    // Initialization
    // ---------------------------
    var controller = this;
    var Appinfo = $resource(APP_DYN_ROOT + "api/apps/:appurl");

    // ---------------------------
    // Scope-related
    // ---------------------------

    /* ATTRIBUTES & METHODS */

    $scope.params = $routeParams;
    $scope.appurl = $routeParams.appurl;
    $scope.appinfo = getAppInfo();

    $scope.test = test;


    /* EVENT HANDLERS */

    $scope.$on("group-added", onGroupAdded); // A group was added in the child directive
    $scope.$on("language-added", onLanguageAdded); // A language was added in the child directive


    // ---------------------------
    // Controller-related
    // ---------------------------


    // ---------------------------
    // Implementations
    // ---------------------------

    /**
     * Asynchronously retrieves the app info through the API.
     */
    function getAppInfo() {
        return Appinfo.get({appurl: $scope.appurl});
    }

    function onGroupAdded(event, args) {
        if(args.success)
            $scope.appinfo.$get({appurl: $scope.appurl});
    } // !onGroupAdded

    function onLanguageAdded(event, args) {
        if(args.success)
            $scope.appinfo.$get({appurl: $scope.appurl});
    } // !onLanguageAdded

    function test() {
        debugger;
    }

} //! AppController


