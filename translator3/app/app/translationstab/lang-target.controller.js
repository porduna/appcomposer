angular
    .module('translateApp')
    .controller('LangTargetController', LangTargetController);


function LangTargetController($scope, $rootScope, $resource) {

    //////////////////
    // Initializations
    //////////////////


    /////////////////
    // Scope-related
    /////////////////

    /* SCOPE DATA */

    $scope.selected = {};

    $scope.objectKeys = $rootScope.objectKeys;
    $scope.all_languages = $rootScope.all_languages;
    $scope.all_groups = $rootScope.all_groups;

    $scope.addGroupError = "";
    $scope.addLanguageError = "";


    // If we don't initialize it, the ui-select does not work.
    $scope.add = {};


    /* SCOPE METHODS */

    $scope.filteredObjectKeys = filteredObjectKeys;

    $scope.languagesThatCanBeAdded = languagesThatCanBeAdded;
    $scope.groupsThatCanBeAdded = groupsThatCanBeAdded;
    $scope.addNewLanguage = addNewLanguage;
    $scope.addNewGroup = addNewGroup;
    $scope.onTargetSelected = onTargetSelected;

    /* SCOPE WATCHES */

    // Initialize the default value when it is ready.
    $scope.$watch("appinfo.translations", function (newval, oldval) {
        if (newval != undefined)
            $scope.selected.lang = "all_ALL";
    });

    // Handle the selected event for the Lang field.
    $scope.$watch("selected.lang", onLangSelected);

    // Handle the selected event for the Target field.
    $scope.$watch("selected.target", onTargetSelected);


    ///////////////////
    // Implementations
    ///////////////////

    /**
     * Filters the specified map.
     * @param map
     * @param search
     * @returns {*}
     */
    function filteredObjectKeys(map, search) {
        var keys = Object.keys(map);
        var filteredKeys = [];

        if (search.length == 0)
            return keys;

        angular.forEach(keys, function (lang, index) {
            var text = $scope.appinfo.translations[lang].name;
            if (text.toLowerCase().indexOf(search.toLowerCase()) != -1)
                filteredKeys.push(lang);
        });

        return filteredKeys;
    }

    /**
     * Returns the list of languages that can be added. That is, the list of
     * all languages except those that are present already.
     */
    function languagesThatCanBeAdded() {
        var all = $scope.objectKeys($scope.all_languages);
        var existing = $scope.objectKeys($scope.appinfo.translations);

        return $(all).not(existing).get();
    } // !languagesThatCanBeAdded


    function groupsThatCanBeAdded() {
        if($scope.selected == undefined || $scope.selected.lang_info == undefined)
            return [];
        var existing = $scope.objectKeys($scope.selected.lang_info.targets);
        var all = $scope.objectKeys($scope.all_groups);

        return $(all).not(existing).get();
    } // !groupsThatCanBeAdded


    /**
     * Adds a new language to the current application.
     */
    function addNewLanguage() {
        $scope.appinfo.translations[$scope.add.lang] = {
            name: $scope.all_languages[$scope.add.lang],
            targets: {
                "ALL" : {
                    name: "ALL",
                    modified_date: null,
                    created_date: null,
                    translated: 0,
                    items: 0
                }
            }
        };
    } // !addNewLanguage


    function addNewGroup() {
        $scope.appinfo.translations[$scope.selected.lang].targets[$scope.add.group] = {
            name: $scope.all_groups[$scope.add.group],
            modified_date: null,
            created_date: null,
            translated: 0,
            items: 0
        }

    } // !addNewGroup


    function onLangSelected(newval, oldval) {
        if (newval == undefined)
            return;

        $scope.selected.lang_info = $scope.appinfo.translations[$scope.selected.lang];

        $scope.selected.target = "ALL";
        $scope.onTargetSelected();
    }

    function onTargetSelected(newval, oldval) {
        if (newval == undefined)
            return;

        $scope.selected.target_info = $scope.selected.lang_info.targets[$scope.selected.target];
    }

} // !LangTargetController