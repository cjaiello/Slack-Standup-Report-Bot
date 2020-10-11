$(document).ready(function(){
    function fadeInAndOut(item) {
        item.fadeIn(1000).delay(5000).fadeOut(1000, function() {
            if (item.next().length) {
                fadeInAndOut(item.next());
            } else {
                fadeInAndOut(firstItem);
            }
        });
    };
    var firstItem = $(".header-image-quotes li:first-child");
    fadeInAndOut(firstItem);
});