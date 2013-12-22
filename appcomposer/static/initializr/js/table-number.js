(function($){
  $.fn.extend({
    tableAddCounter: function(options) {
      
      // default options 
      var defaults = {
        title: '#',
        start: 1,
        id: false, 
        class: false,
      };

      // options provided by the user
      var options = $.extend({}, defaults, options);

      return $(this).each(function(){
        // Make sure this is a table tag
        if($(this).is('table')){

          // Add column title unless set to 'false'
          if(!options.title) options.title = '';
          $('th:first-child, thead td:first-child', this).each(function(){
            var tagName = $(this).prop('tagName');
            $(this).before('<'+tagName+' rowspan="'+$('thead tr').length+'" class="'+options.class+'" id="'+options.id+'">'+options.title+'</'+tagName+'>');
          });
        
          // Add counter starting counter from 'start'
          $('tbody td:first-child', this).each(function(i){
            $(this).before('<td><span class="label label-default">' + (options.start + i) + '</span></td>'); 
          });
        
        }
      });
    }
  });
})(jQuery);
