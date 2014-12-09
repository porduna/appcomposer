angular
    .module("translateApp")
    .directive("acAppsList", acAppsList);


function acAppsList(appsListService) {
    return {
        restrict: "E",
        templateUrl: "apps/apps-list-directive.html",
        link: function (scope, element, attrs) {

            var _table = $(element).find("#appsearch-table");

            initializeAppSearch();

            var appsPromise = appsListService.retrieve();
            appsPromise.then(function(apps){
                if(apps.status == "200") {
                    apps = apps.data.translations;
                    fillAppsList(apps);
                } else {
                    console.error("[ERROR]: Could not retrieve data");
                }

            });

            function fillAppsList(apps) {
                for (var i = 0; i < apps.length; i++) {
                    var app = apps[i];

                    debugger;
                    // Make the description shorter if needed.
                    var desc = app["description"];
                    if (desc.length > 50)
                        desc = desc.substring(0, 50) + "...";

                    _table.row.add([app["title"], desc, app["app_type"]]);

                    var desc_td = appsearch.cell(i, 1).node();
                    $(desc_td).attr("title", app["description"]);
                }

                appsearch.draw();
            }

            function initializeAppSearch() {
                appsearch = _table.DataTable({
                    language: {
//                        "search": "{{ gettext("Search:") }}",
//                        "processing": "{{ gettext("Processing...") }}",
//                        "info": "{{ gettext("Showing page _PAGE_ of _PAGES_") }}",
//                        "lengthMenu": "{{ gettext("Display _MENU_ records per page") }}",
//                        "zeroRecords": "{{ gettext("Nothing found") }}",
//                        "infoEmpty": "{{ gettext("No records available") }}",
//                        "infoFiltered": "{{ gettext("(filtered from _MAX_ total records)") }}",
//                        "paginate": {
//                            first: "{{ gettext("First") }}",
//                            previous: "{{ gettext("Previous") }}",
//                            next: "{{ gettext("Next") }}",
//                            last: "{{ gettext("Last") }}"
//                          },

                    },
                    autoWidth: false,
                    lengthChange: true,
                    columnDefs: [
                        {
                            "targets": 2,
                            "sortable": false,
                            "width": "50%"
                        }
                    ]
                });
            }

        } // !link
    }; //! return
} //! function