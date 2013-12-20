"use strict";

var ut = ut || {}
ut.commons = ut.commons || {}
ut.commons.utils = ut.commons.utils || {}

ut.commons.utils.printDebugInformation = function () {
   console.log("*** ut.commons.utils.printDebugInformation ***")

   if (typeof osapi == 'object') {
      console.log("osapi: " + osapi);
   } else {
      console.log("osapi is undefined.");
   }
   if (typeof gadgets == 'object') {
      console.log("gadgets: " + gadgets);
   } else {
      console.log("gadgets is undefined.");
   }

   if (typeof osapi == 'object') {
      var batch = osapi.newBatch();
      batch.add('context', osapi.context.get());
      batch.add('viewer', osapi.people.getOwner());
      batch.add('app', osapi.apps.get({contextId: "@self"}));
      batch.execute(function (response) {
         console.log("actor.id (viewer.id): " + response.viewer.id);
         var uncapitalizedContextType = response.context.contextType.slice(1);
         var contextType = uncapitalizedContextType.charAt(0).toUpperCase() + uncapitalizedContextType.slice(1);
         console.log("objectType (context.contextType): " + contextType);
         console.log("generator.id (app.id): " + response.app.id);

      });
   }

   console.log("*** /debugInformation ***")
}

/**
 * If "gadgets" object exists, call gadgets.window.adjustHeight.
 * @return {undefined}
 */
ut.commons.utils.gadgetResize = function resize() {
   if (typeof gadgets == 'object') {
      console.log("calling gadgets.window.adjustHeight().");
      gadgets.window.adjustHeight();
   }
}

/**
 * Generates and returns a random UUID.
 * @return {String}   Returns a string value containing a random UUID
 */
ut.commons.utils.generateUUID = function () {
   return s4() + s4() + '-' + s4() + '-' + s4() + '-' +
       s4() + '-' + s4() + s4() + s4();

   function s4() {
      return Math.floor((1 + Math.random()) * 0x10000)
          .toString(16)
          .substring(1);
   };
}

function isStringEmpty(inputStr) {
   if (null == inputStr || "" == inputStr) {
      return true;
   } else {
      return false;
   }
}

/**
 * Converts a string with line breaks into a string with <br/>s.
 * Useful to get a multi-line text from a textarea and put it into a <p>.
 * @return {String}   Returns a string with line breaks replaced by <br> tags.
 */
function nl2br(str, is_xhtml) {
   var breakTag = (is_xhtml || typeof is_xhtml === 'undefined') ? '<br/>' : '<br>';
   return (str + '').replace(/([^>\r\n]?)(\r\n|\n\r|\r|\n)/g, '$1' + breakTag + '$2');
}

ut.commons.utils.getAttributeValue = function (attributes, attributeName, defaultValue) {
   var lcName = attributeName.toLowerCase()
   if (attributes[lcName])
      return attributes[lcName]
   else if (typeof defaultValue !== "undefined")
      return defaultValue
   else
      return null
}

ut.commons.utils.addAttributeValueToOptions = function (attributes, attributeName, options, defaultValue) {
   var lcName = attributeName.toLowerCase()
   if (attributes[lcName])
      options[attributeName] = attributes[lcName]
   else if (typeof defaultValue !== "undefined")
      options[attributeName] = defaultValue
}

ut.commons.utils.getCommonsPath = function () {
   var endPart = "/commons/"
   var commonsPath = "http://go-lab.gw.utwente.nl/sources" + endPart
   var currentHref = window.location.href
   var trySubPath = function (subPath) {
      var index = currentHref.lastIndexOf(subPath)
      if (index >= 0)
         commonsPath = currentHref.substr(0, index) + endPart
      else
         null
   }
   var subPaths = ["/tools/", "/labs/", "/web/"]
   for (var index in subPaths) {
      var subPath = subPaths[index]
      if (trySubPath(subPath))
         break
   }
   return commonsPath
}

ut.commons.utils.commonsPath = ut.commons.utils.getCommonsPath();

ut.commons.utils.getCommonsImagesPath = function () {
   return ut.commons.utils.getCommonsPath() + "images/"
}

ut.commons.utils.commonsImagesPath = ut.commons.utils.getCommonsImagesPath();

ut.commons.utils.getCommonsImagesDataSourcesPath = function () {
   return ut.commons.utils.getCommonsPath() + "images/dataSources/"
}

ut.commons.utils.commonsImagesDataSourcesPath = ut.commons.utils.getCommonsImagesDataSourcesPath();
