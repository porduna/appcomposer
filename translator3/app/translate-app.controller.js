/* THIS IS THE GENERAL CONTROLLER FOR THE APP */

angular
    .module("translateApp")
    .controller("TranslateAppController", TranslateAppController);

function TranslateAppController($scope, $rootScope, $resource) {

    ///////
    // Scope-related
    ///////


    ///////
    //  Root scope related
    ///////
    $rootScope.all_languages = $resource(APP_DYN_ROOT + "api/info/languages").get();
    $rootScope.all_groups = $resource(APP_DYN_ROOT + "api/info/groups").get();

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


} // !TranslateAppController

