const button = document.getElementById('race-button');
button.addEventListener('click', async () => {
  const form = document.getElementById('race-form');
  const result = document.getElementById('race-result');
  button.disabled = true;
  result.textContent = 'Sending two requests for the same slot…';
  const send = () => fetch(form.action, {
    method: 'POST', body: new FormData(form),
    headers: {Accept: 'application/json'}, credentials: 'same-origin',
  });
  try {
    const responses = await Promise.all([send(), send()]);
    const accepted = responses.filter(r => r.status === 201).length;
    const conflicts = responses.filter(r => r.status === 409).length;
    result.textContent = accepted === 1 && conflicts === 1
      ? 'Race complete: 1 reservation accepted (201), 1 duplicate rejected (409).'
      : conflicts === 2
        ? 'This slot was already reserved. Both requests were rejected (409).'
        : 'The race did not finish as expected. Refresh to check your reservations.';
  } catch {
    result.textContent = 'Connection interrupted. A request may have succeeded; refresh to check your reservations.';
  }
  document.getElementById('race-refresh').hidden = false;
});
