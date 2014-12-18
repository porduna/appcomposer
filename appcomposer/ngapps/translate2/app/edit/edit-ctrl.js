angular
    .module("translateApp")
    .controller("EditCtrl", EditCtrl);

function EditCtrl($scope, $resource, $routeParams) {
    TranslationInfo = $resource(APP_DYN_ROOT + "translations/bundle/:appurl/:srclang/:srcgroup/:targetlang/:targetgroup");

    $scope.params = $routeParams;
    $scope.appurl = $routeParams.appurl;

    $scope.appinfo = TranslationInfo.get({appurl: $scope.appurl, srclang: "all_ALL", srcgroup: "ALL", targetlang: "all_ALL", targetgroup: "ALL"});
}