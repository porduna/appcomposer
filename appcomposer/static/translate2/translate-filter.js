//! Filter for i18n. Not yet really implemented.

angular
    .module("translateApp")
    .filter("translate", translateFilter);


function translateFilter() {
    return translate;

    function translate(text) {
        return text;
    }
}