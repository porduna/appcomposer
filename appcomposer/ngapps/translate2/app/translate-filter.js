//! Filter for i18n. Not yet really implemented.

angular
    .module("translateApp")
    .filter("translate", translateFilter);


function translateFilter() {
    return translate;

    function translate(text) {
        var ret = TRANSLATIONS[text];
        if (ret != undefined)
            return ret;
        else
            return text;
    }
}