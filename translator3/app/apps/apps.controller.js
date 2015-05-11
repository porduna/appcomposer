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
    $scope.getGradientColor = getGradientColor;
    $scope.getBadgeTitle = getBadgeTitle;

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

        angular.forEach(app.translated_languages, function (value, key) {
            if (app.original_languages_simplified.indexOf(extractLangName(key)) == -1) {
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

    /**
     * Method from stackoverflow to get a linear gradient between two colors.
     * http://stackoverflow.com/questions/3080421/javascript-color-gradient
     * @param start_color
     * @param end_color
     * @param percent
     */
    function getGradientColor(start_color, end_color, percent) {
        // strip the leading # if it's there
        start_color = start_color.replace(/^\s*#|\s*$/g, '');
        end_color = end_color.replace(/^\s*#|\s*$/g, '');

        // convert 3 char codes --> 6, e.g. `E0F` --> `EE00FF`
        if (start_color.length == 3) {
            start_color = start_color.replace(/(.)/g, '$1$1');
        }

        if (end_color.length == 3) {
            end_color = end_color.replace(/(.)/g, '$1$1');
        }

        // get colors
        var start_red = parseInt(start_color.substr(0, 2), 16),
            start_green = parseInt(start_color.substr(2, 2), 16),
            start_blue = parseInt(start_color.substr(4, 2), 16);

        var end_red = parseInt(end_color.substr(0, 2), 16),
            end_green = parseInt(end_color.substr(2, 2), 16),
            end_blue = parseInt(end_color.substr(4, 2), 16);

        // calculate new color
        var diff_red = end_red - start_red;
        var diff_green = end_green - start_green;
        var diff_blue = end_blue - start_blue;

        diff_red = ( (diff_red * percent) + start_red ).toString(16).split('.')[0];
        diff_green = ( (diff_green * percent) + start_green ).toString(16).split('.')[0];
        diff_blue = ( (diff_blue * percent) + start_blue ).toString(16).split('.')[0];

        // ensure 2 digits by color
        if (diff_red.length == 1)
            diff_red = '0' + diff_red

        if (diff_green.length == 1)
            diff_green = '0' + diff_green

        if (diff_blue.length == 1)
            diff_blue = '0' + diff_blue

        return '#' + diff_red + diff_green + diff_blue;
    } // !getGradientColor

    /**
     * Gets the title for the specified badge.
     */
    function getBadgeTitle(langname, lang) {
        var progress = sprintf("Translation progress: %s", $filter("percentage")(lang.progress, 0) );

        if(lang.original) {
            return "This translation is provided by the original developer and will not be applied automatically." + progress;
        } else {
            return "" + progress;
        }
    } // !getBadgeTitle

} // !AppsController