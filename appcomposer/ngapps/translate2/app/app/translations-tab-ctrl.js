angular
    .module("translateApp")
    .controller("TranslationsTabCtrl", TranslationsTabCtrl);

function TranslationsTabCtrl($scope) {
    $scope.selected = {};
    $scope.objectKeys = objectKeys;
    $scope.filteredObjectKeys = filteredObjectKeys;

    $scope.$watch("appinfo.translations", function() {
        console.log("HAI");
        $scope.selected.lang = "all_ALL";
    });

    function objectKeys(map) {
        return Object.keys(map);
    }

    function filteredObjectKeys(map, search) {
        var keys = Object.keys(map);
        var filteredKeys = [];

        if(search.length == 0)
            return keys;

        angular.forEach(keys, function(lang, index) {
            var text = $scope.appinfo.translations[lang].name;
            if(text.toLowerCase().indexOf(search.toLowerCase()) != -1)
                filteredKeys.push(lang);
        });

        return filteredKeys;
    }
}