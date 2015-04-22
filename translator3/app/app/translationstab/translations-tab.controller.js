angular
    .module("translateApp")
    .controller("TranslationsTabController", TranslationsTabController);

function TranslationsTabController($scope, $log) {

    $scope.translatedPercent = translatedPercent;
    $scope.translatedPercentStr = translatedPercentStr;


    function translatedPercentStr(selected) {
        try {
            var data = $scope.appinfo.translations[selected].targets["ALL"];
            var ratio = data.translated / data.items;
            return "" + data.translated + " / " + data.items + " (" + (ratio * 100.0).toFixed(2) + "%)";
        } catch(err) {
            return "N/A";
        }
    } // !translatedPercent

    function translatedPercent(selected) {
        try {
            var data = $scope.appinfo.translations[selected].targets["ALL"];
            var ratio = data.translated / data.items;
            return ratio;
        } catch(err) {
            return undefined;
        }
    } // !translatedPercent

} //! TranslationsTabCtrl