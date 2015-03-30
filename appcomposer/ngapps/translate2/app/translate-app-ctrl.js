/* THIS IS THE GENERAL CONTROLLER FOR THE APP */

angular
    .module("translateApp")
    .controller("TranslateAppCtrl", TranslateAppCtrl);

function TranslateAppCtrl($scope, $rootScope, $resource) {
    $rootScope.objectKeys = objectKeys;
    $rootScope.dbg = function() { debugger; };

    $scope.all_languages = $resource(APP_DYN_ROOT + "info/languages").get();
    $scope.all_groups = $resource(APP_DYN_ROOT + "info/groups").get();


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
}

