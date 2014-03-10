/**
 * Created with IntelliJ IDEA.
 * User: lars
 */

"use strict";

var ut = ut || {}
ut.commons = ut.commons || {}
ut.commons.metadata = ut.commons.metadata || {}

ut.commons.metadata.Metadata = function(jsonURL, callback) {

    console.log("Initializing Metadata.");

    var metadata = {};

    $.ajax({
        url: jsonURL,
        dataType: "json",
        success: readLabMetaData,
        error: setDefaultLabMetadata,
        complete: returnMetadataToCaller
    });

    function readLabMetaData(labMetadata) {
        console.log("reading lab metadata from "+jsonURL+".");
        this.metadata = labMetadata;
    }

    function returnMetadataToCaller() {
        callback(metadata);
    }

    function setDefaultLabMetadata() {
        console.log("reading lab metadata from "+jsonURL+" failed, falling back to default metadata.");
        metadata = {
            "lab_name": "default lab name",
            "domain": "default domain",
            "topic": "default topic",

            "input_variables": [
                {
                    "name": "length",
                    "symbol": "L",
                    "unit": "m",
                    "type": "double",
                    "values": "0.01 - 10.0"
                },
                {
                    "name": "mass",
                    "symbol": "M",
                    "unit": "kg",
                    "type": "double",
                    "values": "0.01 - 10.0"
                },
                {
                    "name": "time",
                    "symbol": "T",
                    "unit": "s",
                    "type": "double",
                    "values": "0.0 - 255.0"
                },
                {
                    "name": "electric current",
                    "symbol": "I",
                    "unit": "A",
                    "type": "double",
                    "values": "0.0 - 1000.0"
                },
                {
                    "name": "object density",
                    "symbol": "ρ",
                    "unit": "m/V",
                    "type": "double",
                    "values": "0.0 - 1000.0"
                },
                {
                    "name": "fluid density",
                    "symbol": "ρ",
                    "unit": "m/V",
                    "type": "double",
                    "values": "0.0 - 1000.0"
                },
                {
                    "name": "object",
                    "symbol": "",
                    "unit": "",
                    "type": "",
                    "values": ""
                }
            ],

            "output_variables": [
                {
                    "name": "force",
                    "symbol": "N",
                    "unit": "kg*m*s^-2",
                    "type": "double",
                    "values": "0.0 - 1000.0"
                },
                {
                    "name": "voltage",
                    "symbol": "V",
                    "unit": "kg*m^1*s^-3*A^-1",
                    "type": "double",
                    "values": "0.0 - 1000.0"
                },
                {
                    "name": "energy",
                    "symbol": "J",
                    "unit": "kg*m^2*s-2",
                    "type": "double",
                    "values": "0.0 - 1000.0"
                }
            ],

            "relations": [
                {
                    "speed": "speed = length / time"
                },
                {
                    "watt": "watt = energy / time"
                }
            ]
        }
    }
}

