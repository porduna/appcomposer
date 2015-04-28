angular
    .module("translateApp")
    .controller("EditController", EditController);

function EditController($scope, $resource, $routeParams, $log, $modal, $timeout, $interval) {

    /////////
    // Initialization
    /////////

    var TranslationInfo = $resource(APP_DYN_ROOT + "api/apps/bundles/:lang/:target"); // Query parameters are needed
    var Appinfo = $resource(APP_DYN_ROOT + "api/apps");
    var CheckModifications = $resource(APP_DYN_ROOT + "api/apps/bundles/:lang/:target/checkModifications"); // Query parameters are needed

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

    $scope.translationInfo = undefined;
    retrieveTranslationInfo();

    $scope.appinfo.$promise.then(onGetSuccess, onGetError);

    $scope.checkModifications = undefined;
    $scope.checkModificationsInterval = $interval(doCheckModifications, 6000);

    /* METHODS */

    $scope.changeSourceLanguage = changeSourceLanguage;

    /* EVENTS */

    // Event to go to the next item.
    $scope.$on("edit-go-next", onEditGoNext);

    /////////
    // Implementations
    /////////

    /**
     * Setups the check modifications trigger.
     */
    function doCheckModifications() {
        retrieveCheckModifications();

        $scope.checkModifications.$promise.then(onCheckModificationsSuccess, onCheckModificationsError);
    } // !setupCheckModifications

    /**
     * If apparently the bundle has been modified recently, we need to refresh it.
     * We ignore changes made by ourselves.
     * @param result
     */
    function onCheckModificationsSuccess(result) {
        if(result.modificationDateByOther == undefined) {
            // An error occurred, etc.
            // Ignore it for now.
            $log.error("checkModifications: Unknown error. Result: ");
            $log.debug(result);
            return;
        }

        var date = new Date(result.modificationDateByOther);

        // Compare against the last update date.
        var lastDate = new Date($scope.translationInfo.modificationDateByOther);
        if(lastDate < date) {
            $log.debug("Bundle change detected: Refreshing.");
            retrieveTranslationInfo();
        } else {
            // $log.debug("No changes according to date");
        }
    } // !onCheckModificationsSuccess

    function onCheckModificationsError() {
        // Do nothing. The interval will make the request again on its own.
    } // !onCheckModificationsError

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

    /**
     * Retrieve or refresh the translation info.
     */
    function retrieveTranslationInfo() {
        var args = {app_url: $scope.appurl, srclang: $scope.bundle.srclang,
            srcgroup: $scope.bundle.srcgroup, lang: $scope.bundle.targetlang, target: $scope.bundle.targetgroup};

        if($scope.translationInfo == undefined)
            $scope.translationInfo = TranslationInfo.get(args);
        else
            $scope.translationInfo.$get(args);

        $scope.translationInfo.$promise.then(onGetSuccess, onGetError);
    } // !retrieveTranslationInfo

    /**
     * GET request to get the modification date and update if needed.
     * @returns {*}
     */
    function retrieveCheckModifications() {
        var args = {app_url: $scope.appurl, srclang: $scope.bundle.srclang,
            srcgroup: $scope.bundle.srcgroup, lang: $scope.bundle.targetlang, target: $scope.bundle.targetgroup};

        if($scope.checkModifications == undefined)
            $scope.checkModifications = CheckModifications.get(args);
        else
            $scope.checkModifications.$get(args);

    } // !getCheckModifications

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