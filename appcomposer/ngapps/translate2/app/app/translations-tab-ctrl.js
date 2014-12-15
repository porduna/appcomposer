angular
    .module("translateApp")
    .controller("TranslationsTabCtrl", TranslationsTabCtrl);

function TranslationsTabCtrl($scope) {
    $scope.selected = {};

    $scope.$watch("appinfo.translations", function() {
        console.log("HAI");
        $scope.selected.lang = "all_ALL";
    });
}