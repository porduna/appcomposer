angular
    .module("translateApp")
    .directive("acLangTarget", acLangTargetDirective);


function acLangTargetDirective() {
    return {
        restrict: "E",
        templateUrl: "app/translationstab/lang-target.html",
        scope: {
            appinfo: "=",
            selected: "="
        },
        link: langTargetLink
    };


    function langTargetLink(scope, element, attrs) {
        scope.selected = {};
        scope.objectKeys = objectKeys;
        scope.filteredObjectKeys = filteredObjectKeys;
        scope.onTargetSelected = onTargetSelected;

        // Initialize the default value when it is ready.
        scope.$watch("appinfo.translations", function (newval, oldval) {
            if (newval != undefined)
                scope.selected.lang = "all_ALL";
        });

        // Handle the selected event for the Lang field.
        scope.$watch("selected.lang", onLangSelected);

        // Handle the selected event for the Target field.
        scope.$watch("selected.target", onTargetSelected);


        function objectKeys(map) {
            if (map == undefined)
                return [];
            return Object.keys(map);
        }

        function filteredObjectKeys(map, search) {
            var keys = Object.keys(map);
            var filteredKeys = [];

            if (search.length == 0)
                return keys;

            angular.forEach(keys, function (lang, index) {
                var text = scope.appinfo.translations[lang].name;
                if (text.toLowerCase().indexOf(search.toLowerCase()) != -1)
                    filteredKeys.push(lang);
            });

            return filteredKeys;
        }

        function onLangSelected(newval, oldval) {
            if (newval == undefined)
                return;

            scope.selected.lang_info = scope.appinfo.translations[scope.selected.lang];

            scope.selected.target = "ALL";
            scope.onTargetSelected();
        }

        function onTargetSelected(newval, oldval) {
            if (newval == undefined)
                return;

            scope.selected.target_info = scope.selected.lang_info.targets[scope.selected.target];
        }
    }
} //! acLangTargetDirective

