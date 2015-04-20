angular
    .module("translateApp")
    .controller("PreviewTabController", PreviewTabController);


function PreviewTabController($scope, $log, $sce) {
    SHINDIG_SERVER = 'http://shindig2.epfl.ch';
    RELATIVE_URL = '/gadgets/ifr?nocache=0&url=';

    $scope.preview = {};
    //$scope.preview.url = $sce.trustAsResourceUrl(SHINDIG_SERVER + RELATIVE_URL + encodeURIComponent($scope.appurl));

    $scope.$on("setPreviewUrl", onSetPreviewUrl);

    // As of now, lang to preview is not selectable.


    function onSetPreviewUrl(ev, url) {
        $log.debug("On setPreviewUrl: " + url);
        $scope.preview.url = $sce.trustAsResourceUrl(SHINDIG_SERVER + RELATIVE_URL + encodeURIComponent(url));
    } // !onPreviewSelected

} // !PreviewTabController