angular
    .module("translateApp")
    .controller("EditController", EditController);

function EditController($scope, $resource, $routeParams, $log, $modal) {

    /////////
    // Initialization
    /////////

    var TranslationInfo = $resource(APP_DYN_ROOT + "api/apps/bundles/:lang/:target"); // Query parameters are needed
    var Appinfo = $resource(APP_DYN_ROOT + "api/apps");

    /////////
    // Scope related
    /////////

    /* DATA */

    $scope.params = $routeParams;
    $scope.appurl = $routeParams.appurl;

    $scope.status = {}; // For holding error status and the like.

    $scope.bundle = {};
    $scope.bundle.appurl = $scope.appurl;
    $scope.bundle.srclang = "all_ALL";
    $scope.bundle.srcgroup = "ALL";
    $scope.bundle.targetlang = $routeParams.targetlang;
    $scope.bundle.targetgroup = $routeParams.targetgroup;

    $scope.appinfo = Appinfo.get({app_url: $scope.appurl});
    $scope.translationInfo = TranslationInfo.get({app_url: $scope.appurl, srclang: $scope.bundle.srclang,
        srcgroup: $scope.bundle.srcgroup, lang: $scope.bundle.targetlang, target: $scope.bundle.targetgroup});

    $scope.translationInfo.$promise.then(onGetSuccess, onGetError);
    $scope.appinfo.$promise.then(onGetSuccess, onGetError);

    /* METHODS */

    $scope.changeSourceLanguage = changeSourceLanguage;

    /* EVENTS */

    // Event to go to the next item.
    $scope.$on("edit-go-next", onEditGoNext);

    /////////
    // Implementations
    /////////

    function changeSourceLanguage() {
        $log.debug("[changeSourceLanguage]");

        var modal = $modal.open({
            templateUrl: 'edit/change-source/change-source.modal.html',
            controller: 'ChangeSourceController',
            controllerAs: 'changeSourceController',
            backdrop: true,
            keyboard: true,
            size: 'lg',
            scope: $scope
        });

        modal.result.then(onSourceLanguageChanged, onSourceLanguageChangeDismissed);
    } // !changeSourceLanguage

    function onSourceLanguageChanged(selected) {
        $log.debug("[onSourceLanguageChanged]");

        $scope.bundle.srclang = selected.lang;
        $scope.bundle.srcgroup = selected.target;

        // TODO: Refresh only if we did not select the same source language.
        $scope.translationInfo = TranslationInfo.get({appurl: $scope.appurl, srclang: $scope.bundle.srclang,
            srcgroup: $scope.bundle.srcgroup, targetlang: $scope.bundle.targetlang, targetgroup: $scope.bundle.targetgroup});
    } // !onSourceLanguageChanged


    function onSourceLanguageChangeDismissed() {
        $log.debug("[onSourceLanguageChangeDismissed]");
    } // !onSourceLanguageChangeDismissed


    /**
     * Switches the active message from the one specified by the event,
     * to the next one.
     * @param args
     */
    function onEditGoNext(args, item) {
        $log.debug("Broadcasting edit-message-focused from EDIT. We should focus: " + (item.index + 1));
        $scope.$broadcast("edit-message-focused", {index: item.index + 1})
    } // !onMessageEditGoNext


    function onGetSuccess() {

    } // !onThenSuccess

    /**
     * To be called when the Appinfo or Translation requests fail.
     */
    function onGetError() {
        $log.error("Handling API request error");
        $scope.status.error = {};
        $scope.status.error.message = error.data;
        $scope.status.error.code = error.status;
        $scope.status.error.statusText = error.statusText;
    } // !onGetError

} // !EditController