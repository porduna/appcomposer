/* THIS IS THE GENERAL CONTROLLER FOR THE APP */

angular
    .module("translateApp")
    .controller("TranslateAppController", TranslateAppController);

function TranslateAppController($scope, $rootScope, $resource, $location) {

    // -----------
    // Initial
    // -----------

    // Handle authentication: If the current URL is not auth'ed, redirect.
    $scope.auth_result = $resource(APP_DYN_ROOT + "api/authn/:url").get({url: $location.absUrl()});
    $scope.auth_result.$promise.then(onAuthResultAvailable);

    // -----------
    // Scope-related
    // -----------


    ///////
    //  Root scope related
    ///////
    $rootScope.all_languages = $resource(APP_DYN_ROOT + "api/info/languages").get();
    $rootScope.all_groups = $resource(APP_DYN_ROOT + "api/info/groups").get();
    $rootScope.default_language = $resource(APP_DYN_ROOT + "api/default-language").get();

    $rootScope.objectKeys = objectKeys;
    $rootScope.dbg = function() { debugger; };


    ///////
    // Implementations
    ///////

    function objectKeys(obj) {
        if(obj == undefined)
            return [];

        var ret = [];
        var keys = Object.keys(obj);
        if(keys == undefined)
            return [];

        for(var i = 0; i < keys.length; i++) {
            if(keys[i].indexOf('$') != 0)
                ret.push(keys[i]);
        }

        return ret;
    }

    /**
     * If we are not auth we need to redirect to the auth screen. We do not redirect if we are in localhost
     * or if we carry a noauth flag.
     */
    function onAuthResultAvailable(data) {
        if(data.result == "fail" && /*$location.host() != "localhost" &&*/ $location.search().noauth == undefined) {
            window.location = data.redirect;
        }
    } // !onAuthResultAvailable


} // !TranslateAppController

