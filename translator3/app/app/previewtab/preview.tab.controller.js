angular
    .module("translateApp")
    .controller("PreviewTabController", PreviewTabController);


function PreviewTabController($scope, $log, $sce) {

    // -----------------------
    // Initialization
    // -----------------------

    SHINDIG_SERVER = 'http://shindig2.epfl.ch';
    RELATIVE_URL = '/gadgets/ifr?nocache=0&url=';


    // -----------------------
    // Data
    // -----------------------

    $scope.preview = {};
    //$scope.preview.url = $sce.trustAsResourceUrl(SHINDIG_SERVER + RELATIVE_URL + encodeURIComponent($scope.appurl));

    // -----------------------
    // Scope events & watches
    // -----------------------

    $scope.$on("setPreviewUrl", onSetPreviewUrl);

    $scope.$watch("selected_target.lang", onSelectedTargetChanged);

    // As of now, lang to preview is not selectable.


    // -----------------------
    // Implementations
    // -----------------------

    function onSetPreviewUrl(ev, url) {
        var lang = "";

        try {
            lang = $scope.selected_target.lang;
            lang = lang.replace(/(.*)_(.*)/, '$1');
        } catch(err) {
        }

        $log.debug("On setPreviewUrl: " + url);
        $scope.preview.url = $sce.trustAsResourceUrl(SHINDIG_SERVER + RELATIVE_URL + encodeURIComponent(url) +
            "&lang=" + encodeURIComponent(lang));
    } // !onPreviewSelected

    function onSelectedTargetChanged(newval, oldval) {
        if(newval != oldval) {
            // Refresh the preview.
            onSetPreviewUrl(undefined, $scope.$parent.appurl);
        }
    } // !onSelectedTargetChanged
} // !PreviewTabController