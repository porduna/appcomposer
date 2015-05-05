angular
    .module("translateApp")
    .directive("acPreview", acPreview);


function acPreview($log) {
    return {
        restrict: "E",
        templateUrl: "edit/preview/preview.directive.html",
        link: acPreviewLink,
        controller: "PreviewController",
        controllerAs: "previewController",
        scope: {
            lang: "=lang",
            appurl: "=appurl"
        }
    }; // !return


    function acPreviewLink(scope, element, attrs, ctrl) {

        scope.doRefresh = doRefresh;

        // ---------------
        // Implementations
        // ---------------

        function doRefresh() {
            $log.debug("Refreshing iframe");
            var iframe = element.find("iframe");
            var srcnow = iframe.attr("src");
            iframe.attr("src", srcnow);
        } // !doRefresh

    } // !acPreviewLink

} // !acPreview

