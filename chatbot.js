
$(function () {

    $('#displayname').val(prompt('Entre com seu nome:', ''));

    var $chatbox = $('.chatbox'),
        $chatboxTitle = $('.chatbox__title'),
        $chatboxTitleClose = $('.chatbox__title__close'),
        $chatboxCredentials = $('.chatbox__credentials');
    $chatbox.removeClass('chatbox--empty');

    $chatboxTitle.on('click', function () {
        $chatbox.toggleClass('chatbox--tray');
    });
    $chatboxTitleClose.on('click', function (e) {
        e.stopPropagation();
        $chatbox.addClass('chatbox--closed');
    });
    $chatbox.on('transitionend', function () {
        if ($chatbox.hasClass('chatbox--closed')) $chatbox.remove();
    });


    var chat = $.connection.chatHub;

    chat.client.addNewMessageToPage = function (name, message) {

        var displayname = $('#displayname').val();
        var msgBody = "";

        if (name == displayname)
            msgBody = '<div class="chatbox__body__message chatbox__body__message--left">';
        else
            msgBody = '<div class="chatbox__body__message chatbox__body__message--right">';

        msgBody += '<small class="pull-right text-muted">'
        msgBody += '<span class="glyphicon glyphicon-time"></span> 1 mins ago</small>';
        msgBody += '<img src="http://blogdocarlossantos.com.br/wp-content/uploads/2017/11/Banco-Safra-e1510940510319.png" alt="Picture">';
        msgBody += '<p><span style="color:darkviolet">' + htmlEncode(name) + ':</span><br />' + htmlEncode(message) + '</p></div>'

        $('#chatBody').append(msgBody);
    };

    $('#btnInput').focus();

    $.connection.hub.start().done(function () {
        $('#btnSend').click(function () {

            chat.server.send($('#displayname').val(), $('#btnInput').val());

            $('#btnInput').val('').focus();
        });
    });
});

// This optional function html-encodes messages for display in the page.
function htmlEncode(value) {
    var encodedValue = $('<div />').text(value).html();
    return encodedValue;
}
