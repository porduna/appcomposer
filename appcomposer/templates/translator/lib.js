// Application found and translatable!
$web_link = $(".field-name-field-app-web-link");

$("<div class=\"field field-type-link-field field-label-inline clearfix\"><div class=\"field-label\">Available languages:&nbsp;</div><div class=\"field-items\"><div class=\"field-item even\">{{ translations }} &nbsp; (<a href=\"{{ link }}\">Translate this app</a>)</div></div></div>").insertAfter($web_link);

$web_link = $(".field-name-field-weblink");

$("<div class=\"field field-type-link-field field-label-inline clearfix\"><div class=\"field-label\">Available languages:&nbsp;</div><div class=\"field-items\"><div class=\"field-item even\">{{ translations }} &nbsp; (<a href=\"{{ link }}\">Translate this app</a>)</div></div></div>").insertAfter($web_link);
