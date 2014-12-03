angular.module("translateApp")
    .directive("acAppsList", function ($) {
        return {
            restrict: "E",
            templateUrl: "apps/apps-list-directive.html",
            link: function (scope, element, attrs) {

                initializeAppSearch();

                function initializeAppSearch() {
                    appsearch = $("#appsearch-table").DataTable({
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
    }); //! directive