angular
    .module("translateApp")
    .filter("plaintext", plaintextFilter);


function plaintextFilter() {
    return plaintext;

    function plaintext(html) {
        return String(html).replace(/<[^>]+>/gm, '');
    }
}