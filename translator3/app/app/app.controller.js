angular
    .module("translateApp")
    .controller("AppController", AppController);


function AppController($scope, $routeParams, $resource, $log, $sce) {

    // ---------------------------
    // Initialization
    // ---------------------------
    var controller = this;
    var Appinfo = $resource(APP_DYN_ROOT + "api/apps");

    // ---------------------------
    // Scope-related
    // ---------------------------

    /* ATTRIBUTES & METHODS */

    $scope.params = $routeParams;
    $scope.appurl = $routeParams.appurl;
    $scope.appinfo = getAppInfo();

    $scope.test = test;
    $scope.onPreviewSelected = onPreviewSelected;


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
        return Appinfo.get({app_url: $scope.appurl});
    }

    function onGroupAdded(event, args) {
        if(args.success)
            $scope.appinfo.$get({app_url: $scope.appurl});
    } // !onGroupAdded

    function onLanguageAdded(event, args) {
        if(args.success)
            $scope.appinfo.$get({app_url: $scope.appurl});
    } // !onLanguageAdded

    /**
     * When the preview tab is selected we notify the preview directive so that it refreshes.
     * @param event
     */
    function onPreviewSelected(event) {
        $scope.$broadcast('setPreviewUrl', $scope.appurl);
    } // !onPreviewClicked

    function test() {
        debugger;
    }

} //! AppController


