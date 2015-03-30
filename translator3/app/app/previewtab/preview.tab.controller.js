angular
    .module("translateApp")
    .controller("PreviewTabController", PreviewTabController);


function PreviewTabController($scope, $sce) {
    SHINDIG_SERVER = 'http://shindig.epfl.ch';
    RELATIVE_URL = '/gadgets/ifr?nocache=1&url=';

    $scope.preview = {};
    $scope.preview.url = $sce.trustAsResourceUrl(SHINDIG_SERVER + RELATIVE_URL + $scope.appurl);
}