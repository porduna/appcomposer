angular
    .module("translateApp")
    .controller("PreviewController", PreviewController);


function PreviewController($scope, $log, $sce) {

    // ------------------
    // Initialization
    // ------------------

    SHINDIG_SERVER = 'http://shindig2.epfl.ch';
    RELATIVE_URL = '/gadgets/ifr?nocache=1&url=';


    // ------------------
    // Events & Watches
    // ------------------

    $scope.$watch("appurl", onAppUrlChanged);

    $scope.$on("refresh", onRefresh);

    // ------------------
    // Implementation
    // ------------------

    function onAppUrlChanged(newval, oldval) {
        var rlang = "";

        try {
            rlang = $scope.lang;
            rlang = rlang.replace(/(.*)_(.*)/, '$1');
        } catch(err) {
        }

        $scope.url = $sce.trustAsResourceUrl(SHINDIG_SERVER + RELATIVE_URL + encodeURIComponent($scope.appurl) +
            "&lang=" + encodeURIComponent(rlang));

        $log.debug("URL set to: " + $scope.url);
    } // !onAppUrlChanged


    function onRefresh() {
        $scope.doRefresh();
    } // !onRefresh

} // !PreviewController