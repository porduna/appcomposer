//! Filter for i18n. Not yet really implemented.

angular
    .module("translateApp")
    .filter("translate", translateFilter);


function translateFilter() {
    return translate;

    function translate(text) {
        var trimmed = text.trim();
        
        var ret = TRANSLATIONS[trimmed];
        if (ret != undefined)
            // Keep the trim that we removed for the lookup.
            return text.replace(trimmed, ret);
        else
            return text;
    }
}