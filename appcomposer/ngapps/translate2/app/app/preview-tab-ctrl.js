angular
    .module("translateApp")
    .controller("PreviewTabCtrl", PreviewTabCtrl);


function PreviewTabCtrl($scope, $sce) {
    SHINDIG_SERVER = 'http://shindig.epfl.ch';
    RELATIVE_URL = '/gadgets/ifr?nocache=1&url=';

    $scope.preview = {};
    $scope.preview.url = $sce.trustAsResourceUrl(SHINDIG_SERVER + RELATIVE_URL + $scope.appurl);
}