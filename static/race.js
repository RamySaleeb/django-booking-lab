/* Browser script and dependency-free Node test module. */
(function () {
  'use strict';
  const DEADLINE_MS = 8000;

  async function runRace(send, {setTimer = setTimeout, clearTimer = clearTimeout} = {}) {
    const controller = new AbortController();
    const outcomes = [null, null];
    let timer;
    const deadline = new Promise(resolve => {
      timer = setTimer(() => resolve('timeout'), DEADLINE_MS);
    });
    // Catch both synchronous transport errors and promise rejections. A transport
    // that ignores abort still cannot keep the UI waiting beyond the deadline.
    const requests = outcomes.map((_, index) => Promise.resolve()
      .then(() => send(controller.signal))
      .then(response => { outcomes[index] = response.status; },
        () => { outcomes[index] = 'network-error'; }));
    let timedOut;
    try {
      timedOut = await Promise.race([
        Promise.all(requests).then(() => false),
        deadline.then(() => true),
      ]);
      // Copy before aborting: late completions must not change the reported result.
      return {timedOut, outcomes: [...outcomes]};
    } finally {
      clearTimer(timer);
      controller.abort();
    }
  }

  function describeRace({timedOut, outcomes}) {
    const accepted = outcomes.filter(status => status === 201).length;
    const conflicts = outcomes.filter(status => status === 409).length;
    if (!timedOut && accepted === 1 && conflicts === 1) {
      return 'Race complete: 1 reservation accepted (201), 1 duplicate rejected (409).';
    }
    if (!timedOut && conflicts === 2) {
      return 'This slot was already reserved. Both requests were rejected (409).';
    }
    const reason = timedOut ? 'Stopped waiting after 8 seconds.' : 'The race could not be fully confirmed.';
    const confirmed = accepted ? ` ${accepted} reservation response(s) confirmed (201).` : '';
    return reason + confirmed + ' A request may already have created a reservation, even if it timed out or was aborted. Check your reservations before trying again; no request was retried.';
  }

  function attachRace(document, {fetchRequest = fetch, makeBody = form => new FormData(form), ...clock} = {}) {
    const button = document.getElementById('race-button');
    const form = document.getElementById('race-form');
    const result = document.getElementById('race-result');
    const refresh = document.getElementById('race-refresh');
    let started = false;
    button.addEventListener('click', async () => {
      if (started || button.disabled) return;
      started = true;
      // Keep the control in the tab order while preventing repeat activation.
      button.setAttribute('aria-disabled', 'true');
      result.textContent = 'Sending two requests for the same slot… Waiting up to 8 seconds.';
      const outcome = await runRace(signal => fetchRequest(form.action, {
        method: 'POST', body: makeBody(form), signal,
        headers: {Accept: 'application/json'}, credentials: 'same-origin',
      }), clock);
      result.textContent = describeRace(outcome);
      refresh.textContent = 'Check your reservations →';
      refresh.hidden = false;
      // Keep this page's experiment disabled. Refresh is a safe GET that reveals
      // the actual booking state and gives a fresh slot for any later experiment.
    });
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {runRace, describeRace, attachRace, DEADLINE_MS};
  } else {
    attachRace(document);
  }
})();
