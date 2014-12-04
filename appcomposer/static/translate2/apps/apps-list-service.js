angular
    .module("translateApp")
    .factory("appsListService", appsListService);


function appsListService(appsList) {
    var service = {
        retrieve: retrieve
    };
    return service;


    function retrieve($http) {
        $http.get("")
    }
}