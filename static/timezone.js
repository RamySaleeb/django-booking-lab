/* Device timezone is used only after an explicit button activation. */
(function () {
  const form = document.getElementById('timezone-form');
  const select = document.getElementById('timezone');
  const button = document.getElementById('device-timezone');
  try {
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (![...select.options].some(option => option.value === zone)) return;
    button.hidden = false;
    button.addEventListener('click', () => {
      select.value = zone;
      form.requestSubmit();
    });
  } catch (_) {
    // The server-rendered selector and UTC fallback still work.
  }
})();
