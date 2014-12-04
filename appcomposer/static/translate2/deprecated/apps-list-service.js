angular
    .module("translateApp")
    .factory("appsListService", appsListService);


function appsListService($http) {
    var service = {
        retrieve: retrieve
    };
    return service;


    function retrieve() {
        return $http.get(APP_DYN_ROOT + "translations");
    }
}