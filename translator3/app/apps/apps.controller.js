angular
    .module("translateApp")
    .controller("AppsController", AppsController);


function AppsController($scope, $resource, $compile, $filter, DTOptionsBuilder, DTColumnDefBuilder) {
    $scope.apps = $resource(APP_DYN_ROOT + "api/apps/repository").query();
    $scope.dt = {};

    $scope.selected = {};
    $scope.selected.app = undefined; // To store the selected app.

    $scope.dt.options = DTOptionsBuilder.newOptions()
        .withPaginationType('full_numbers')
        .withDisplayLength(10)
        .withOption("autoWidth", true)
        .withOption("language", {
            "search": $filter("translate")("JQT_SEARCH"),
            "processing": $filter("translate")("JQT_PROCESSING"),
            "info": $filter("translate")("JQT_INFO"),
            "lengthMenu": $filter("translate")("JQT_LEN"),
            "zeroRecords": $filter("translate")("JQT_ZERO"),
            "infoEmpty": $filter("translate")("JQT_INFOEMPTY"),
            "infoFiltered": $filter("translate")("JQT_INFOFILTERED"),
            "paginate": {
                first: $filter("translate")("JQT_PAG_FIRST"),
                previous: $filter("translate")("JQT_PAG_PREV"),
                next: $filter("translate")("JQT_PAG_NEXT"),
                last: $filter("translate")("JQT_PAG_LAST")
            }
        });

    $scope.dt.columnDefs = [
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
    $scope.onlyTranslatedLanguages = onlyTranslatedLanguages;

    // -- EVENTS --

    $scope.$on('event:dataTableLoaded', dataTableLoadedHandler);



    // ------------------------------------
    // IMPLEMENTATIONS
    // ------------------------------------

    /**
     * Extracts an app name. That is, extracts 'en' from 'en_ALL_ALL', for instance.
     */
    function extractLangName(name) {
        return name.split("_")[0];
    } // !extractAppName

    /**
     * Retrieves the dictionary of translations but removing original-translations.
     */
    function onlyTranslatedLanguages(app) {
        var langs = {};

        angular.forEach(app.translated_languages, function(value, key){
            if(app.original_languages_simplified.indexOf(extractLangName(key)) == -1) {
                langs[key] = value;
            }
        });

        return langs;
    } // !onlyTranslatedLanguages

    /**
     * Get a reference to the jQuery DataTable.
     * @param evt
     * @param loadedDT
     */
    function dataTableLoadedHandler(evt, loadedDT) {
        $scope.dt = loadedDT;
    }

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
            $scope.dt.DataTable.row($scope.selected.index).child().hide();
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

        if ($scope.dt != undefined) {
            var table = $scope.dt;
            var row = table.DataTable.row(index);
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

} // !AppsController