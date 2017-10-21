function UpdateRow() {
  var checked = $(this).is(':checked');
  if (checked) {
    $(this)
      .closest('tr')
      .removeClass('ignore');
  } else {
    $(this)
      .closest('tr')
      .addClass('ignore');
  }
}

$(function() {
  $('.togglevisible').each(function() {
    $(this).change(UpdateRow);

    // Ensure rows are correctly updated
    UpdateRow.bind(this)();
  });

  $('.togglechildren').change(function() {
    $(this)
      .closest('table')
      .find('.togglevisible')
      .prop('checked', $(this).is(':checked'))
      .change();
  });

  $('.togglesection').change(function() {
    if ($(this).is(':checked')) {
      $(this)
        .closest('table')
        .removeClass('ignore');
    } else {
      $(this)
        .closest('table')
        .addClass('ignore');
    }
  });
  $('.togglesection').change();

  // Auto-expand text area
  $('textarea').each(function() {
    var self = $(this);

    function update() {
      $(self).css('height', '1em');
      var height = $(self).prop('scrollHeight');
      $(self).css('height', height + 'px');
    }

    $(this)
      .change(update)
      .keyup(update)
      .keydown({ event: 'keydown' }, update);
    $(window).resize(update);
    update();
  });
});
