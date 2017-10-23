// Application found and translatable!
jQuery(document).ready(function () {
    $web_link = jQuery(".field-group.group-info");

    var translations = "";
    {% for translation in translations %}
    translations += "<li>" + {{ translation|tojson }} + "</li>";
    {% endfor %}

    $web_link.append(jQuery("<div class=\"field field_languages less\" style=\"display: flex\"><h4>Languages</h4><ul>" + translations + "</ul></div>"));

});
