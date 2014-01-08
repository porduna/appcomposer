var ut = ut || {}
ut.commons = ut.commons || {}
ut.commons.persistency = ut.commons.persistency || {}

ut.commons.persistency.storeAsFile = function(jsonObject, filename) {
    // create a blob (html5) from jsonObject
    var blob = new Blob([JSON.stringify(jsonObject)], {type: 'text/json'});
    if(navigator.appName.indexOf("Internet Explorer")!=-1){
        // Internet Explorer: save blob as download (to be confirmed by user)
        window.navigator.msSaveBlob(blob, filename);
    } else {
        // other browsers: save blob as download (to be confirmed by user)
        var link = document.createElement("a");
        link.download = filename;
        window.URL = window.webkitURL || window.URL;
        link.href = window.URL.createObjectURL(blob);
        // the link has to be in the DOM for some browsers to be clickable
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

ut.commons.persistency.getFileFromDialog = function(callback) {
    var input = document.createElement("input");
    input.type = "file";
    input.addEventListener("change", function(){
        var file = this.files[0];
        if (file) {
            callback(undefined, file);
        } else {
            callback("ut.commons.persistency: no file selected.", undefined);
        }
    }, false);
    // IE would not trigger the "click" on an element that's not in the DOM
    // -> add invisible element, click, remove
    input.style.display = "none";
    document.body.appendChild(input);
    input.click();
    document.body.removeChild(input);
}

ut.commons.persistency.getJSonObjectFromDialog = function(callback) {
    ut.commons.persistency.getFileFromDialog(handleFile);
    function handleFile(errorMsg, file) {
        if (errorMsg) {
            // getting a file failed, returning the error message
            callback(errorMsg, undefined);
        } else {
            // we got a file, is it JSon?
            try {
                var reader = new FileReader();
                reader.onload = function(e) {
                    var jsonObject = JSON.parse(e.target.result);
                    callback(undefined, jsonObject);
                }
                reader.readAsText(file);
            } catch (exception) {
                callback("ut.commons.persistency: could not parse json.", undefined);
            }
        }
    };
}