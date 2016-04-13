angular
    .module("translateApp")
    .controller("AppsController", AppsController);


function AppsController($scope, $resource, $compile, $filter, $log, $timeout, DTOptionsBuilder, DTColumnDefBuilder) {
    var vm = this;

    $scope.apps = []; // To hold the apps for the current category.
    $scope.all_apps = $resource(APP_DYN_ROOT + "api/apps/repository").query();
    $scope.all_apps.$promise.then(onAppsRetrievalSucceeded, onAppsRetrievalRejected);

    $scope.loadingTable = false;

    $scope.selected = {};
    $scope.selected.app = undefined; // To store the selected app.

    vm.dt = {};
    vm.dt.instance = {};

    $scope.status = {};

    $scope.currentCategory = "";

    $scope.filteringLang = undefined;
    $scope.filteringEnabled = false;
    $scope.languages = $resource(APP_DYN_ROOT + "api/info/languages_default").get();
    $scope.languages.$promise.then(onLanguagesRetrievalSucceeded, onLanguagesRetrievalRejected);

    vm.dt.options = DTOptionsBuilder.newOptions()
        .withPaginationType('full_numbers')
        .withDisplayLength(10)
        .withOption("autoWidth", true)
        .withOption("bRetrieve", false)
        .withOption("language", {
            "search": $filter("translate")("Search:"),
            "processing": $filter("translate")("Processing..."),
            "info": $filter("translate")("Showing page _PAGE_ of _PAGES_"),
            "lengthMenu": $filter("translate")("Display _MENU_ records per page"),
            "zeroRecords": $filter("translate")("Nothing found"),
            "infoEmpty": $filter("translate")("No records available"),
            "infoFiltered": $filter("translate")("(filtered from _MAX_ total records)"),
            "paginate": {
                first: $filter("translate")("First"),
                previous: $filter("translate")("Previous"),
                next: $filter("translate")("Next"),
                last: $filter("translate")("Last")
            }
        });

    vm.dt.columnDefs = [
        DTColumnDefBuilder.newColumnDef(0).notSortable().withOption("width", "30%"),
        DTColumnDefBuilder.newColumnDef(1).notSortable().withOption("width", "40%"),
        DTColumnDefBuilder.newColumnDef(2).notSortable()
    ];


    // ------------------------------------
    // SCOPE RELATED
    // ------------------------------------


    // -- METHODS --

    $scope.selectApp = selectApp;
    $scope.isSelected = isSelected;
    $scope.extractLangName = extractLangName;
    $scope.completionToColor = completionToColor;
    $scope.getGradientColor = getGradientColor;
    $scope.getBadgeTitle = getBadgeTitle;
    $scope.refreshCategory = refreshCategory;
    $scope.getFilteredApps = getFilteredApps;
    $scope.onFilterChanged = onFilterChanged;

    // -- EVENTS --

    // ------------------------------------
    // IMPLEMENTATIONS
    // ------------------------------------


    /**
     * Gets notified when the filter's value is changed,
     * and will thus trigger a refresh of the apps shown.
     */
    function onFilterChanged() {
        refreshCategory($scope.currentCategory);
    } // !onFilterChanged


    /**
     * Gets the apps list, but filtered. If the filtering is not enabled this function will
     * just return the apps as is.
     *
     * @param apps: The 'items' field from the JSON call.
     */
    function getFilteredApps(apps) {

        if(!$scope.filteringEnabled)
            return apps;

        var ret = _.filter(apps, function (app) {
            var filteredLang = app.languages[$scope.filteringLang.code];

            // If the language is not present or if it is not 100% then we have to show this app.
            return (filteredLang === undefined || filteredLang.progress !== 1);
        });

        return ret;
    } // !getFilteredApps
    

    /**
     * Called to select the displayed category. If necessary, this will also
     * apply any filter over the apps that is set, and it will refresh the shown
     * apps.
     */
    function refreshCategory(category) {

        $scope.currentCategory = category;

        // Clear the current selection
        $scope.selected = {};
        $scope.selected.app = undefined;

        angular.forEach($scope.all_apps, function (val, ind) {

            if (val.id == $scope.currentCategory) {

                // Apply the filter (if we must).
                $scope.apps = getFilteredApps(val.items);
            }
        });


    } // !refreshCategory

    /**
     * Called when the apps retrieval method succeeds.
     * @param data
     */
    function onAppsRetrievalSucceeded(data) {
        $log.debug("Apps Retrieval Succeeded");

        //// TODO:
        //// DEbugging only.
        //$scope.all_apps =
        //    [
        //        {
        //            id: "my_labs",
        //            category: "My labs",
        //            items: $scope.apps
        //        },
        //        {
        //            id: "golab_labs",
        //            category: "Go-Lab labs",
        //            items: $scope.apps
        //        }
        //    ];

        // Select default category.
        refreshCategory($scope.all_apps[0].id);

    } // !onAppsRetrievalSucceeded

    /**
     * Called when an error occurs trying to retrieve apps.
     */
    function onAppsRetrievalRejected(error, err, e) {
        $scope.status.error = {};
        $scope.status.error.message = "Not available";
        $scope.status.error.code = "0";
    } // !onAppsRetrievalRejected


    /**
     * Notified when the languages_default API returns a result successfully.
     * @param data
     */
    function onLanguagesRetrievalSucceeded(data) {
        // We need to set the default.
        $scope.filteringLang = _.find(data.languages, function(lang) {
            return lang.code == data.default;
        });
    } // !onLanguagesRetrievalSucceeded


    /**
     * Notified when the languages_default API cant be reached or fails.
     */
    function onLanguagesRetrievalRejected(error, err, e) {
        $scope.status.error = {};
        $scope.status.error.message = "Failed to retrieve languages list";
        $scope.status.error.code = "1";
    } //! onLanguagesRetrievalRejected

    /**
     * Extracts an app name. That is, extracts 'en' from 'en_ALL_ALL', for instance.
     */
    function extractLangName(name) {
        return name.split("_")[0];
    } // !extractAppName


    /**
     * Converts a completion percent of a language into an appropriate
     * HTML color string.
     *
     * @param {float} completion: Completion from 0 to 1.
     * @return {string}: The HTML color. Fully green if 1, fully red if 0.
     */
    function completionToColor(completion) {
        return "FF0000";
    }

    /**
     * Selects an app in the list.
     * @param index: Index of the selected app.
     * @param app: The selected app.
     */
    function selectApp(app, index) {

        // Hide the previous selection.
        if ($scope.selected.index !== undefined) {
            vm.dt.instance.DataTable.row($scope.selected.index).child().hide();
        }

        // If we have re-selected the current selection, it is no longer
        // selected.
        if ($scope.selected.index == index) {
            $scope.selected.index = undefined;
            $scope.selected.app = undefined;
            return;
        }

        $scope.selected.app = app;
        $scope.selected.index = index;

        if (vm.dt.instance.DataTable != undefined) {
            var row = vm.dt.instance.DataTable.row(index);
            var c = row.child($compile("<ac-app-details class='my-disabled-hover' app=selected.app></ac-app-details>")($scope));
            c.show();
        }
    }

    /**
     * Checks if the app is selected.
     * @param app
     */
    function isSelected(app) {
        if ($scope.selected.app == undefined)
            return false;

        var result = app.title === $scope.selected.app.title;
        return result;
    }

    /**
     * Method from stackoverflow to get a green to red gradient
     * http://stackoverflow.com/a/7128796
     * @param percent
     */
    function getGradientColor(percent) {
        var percentColors = [
            {percent: 0.0, color: {r: 0xff, g: 0x00, b: 0}},
            {percent: 0.5, color: {r: 0xff, g: 0xff, b: 0}},
            {percent: 1.0, color: {r: 0x00, g: 0xff, b: 0}}];

        for (var i = 1; i < percentColors.length - 1; i++) {
            if (percent < percentColors[i].percent) {
                break;
            }
        }
        var lower = percentColors[i - 1];
        var upper = percentColors[i];
        var range = upper.percent - lower.percent;
        var rangePct = (percent - lower.percent) / range;
        var pctLower = 1 - rangePct;
        var pctUpper = rangePct;
        var color = {
            r: Math.floor(lower.color.r * pctLower + upper.color.r * pctUpper),
            g: Math.floor(lower.color.g * pctLower + upper.color.g * pctUpper),
            b: Math.floor(lower.color.b * pctLower + upper.color.b * pctUpper)
        };
        var result = 'rgb(' + [color.r, color.g, color.b].join(',') + ')';
        return result;
    } // !getGradientColor

    /**
     * Gets the title for the specified badge.
     */
    function getBadgeTitle(langname, lang) {
        var progress = sprintf("Translation progress: %s", $filter("percentage")(lang.progress, 0));

        if (lang.original) {
            return "This language is provided by the original developer and your adaptation will not be applied automatically." + progress;
        } else {
            return "" + progress;
        }
    } // !getBadgeTitle

} // !AppsController
