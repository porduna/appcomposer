angular
    .module("translateApp")
    .controller("PreviewTabController", PreviewTabController);


function PreviewTabController($scope, $sce) {
    SHINDIG_SERVER = 'http://shindig2.epfl.ch';
    RELATIVE_URL = '/gadgets/ifr?nocache=0&url=';

    $scope.preview = {};
    $scope.preview.url = $sce.trustAsResourceUrl(SHINDIG_SERVER + RELATIVE_URL + encodeURIComponent($scope.appurl));

    // As of now, lang to preview is not selectable.

} // !PreviewTabController