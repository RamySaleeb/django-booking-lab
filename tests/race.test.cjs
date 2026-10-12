const {test} = require('node:test');
const assert = require('node:assert/strict');
const {runRace, describeRace, attachRace, DEADLINE_MS} = require('../static/race.js');

function clock() {
  let fire;
  let cleared = 0;
  return {
    setTimer(callback, delay) { assert.equal(delay, 8000); fire = callback; return 42; },
    clearTimer(id) { assert.equal(id, 42); cleared++; },
    expire() { fire(); },
    get cleared() { return cleared; },
  };
}
const flush = async () => { for (let i = 0; i < 10; i++) await Promise.resolve(); };

for (const statuses of [[201, 409], [409, 201], [409, 409], [500, 409]]) {
  test(`responses ${statuses.join(' + ')} clean up without retry`, async () => {
    const time = clock();
    let calls = 0;
    let signal;
    const result = await runRace(s => { signal = s; return Promise.resolve({status: statuses[calls++]}); }, time);
    assert.deepEqual(result, {timedOut: false, outcomes: statuses});
    assert.equal(calls, 2);
    assert.equal(time.cleared, 1);
    assert.equal(signal.aborted, true);
    const text = describeRace(result);
    assert.match(text, statuses.includes(500) ? /may already have created/ : statuses.includes(201) ? /1 reservation accepted/ : /Both requests were rejected/);
  });
}

test('a rejected request retains the other confirmed response', async () => {
  const time = clock();
  let calls = 0;
  const result = await runRace(() => ++calls === 1 ? Promise.resolve({status: 201}) : Promise.reject(new Error('offline')), time);
  assert.deepEqual(result.outcomes, [201, 'network-error']);
  assert.match(describeRace(result), /1 reservation response\(s\) confirmed/);
  assert.equal(time.cleared, 1);
});

test('never-settling transport is bounded even when it ignores abort', async () => {
  const time = clock();
  let calls = 0;
  let signal;
  let finishLate;
  const pending = runRace(s => {
    signal = s;
    return ++calls === 1 ? Promise.resolve({status: 201}) : new Promise(resolve => { finishLate = resolve; });
  }, time);
  await flush();
  time.expire();
  const result = await pending;
  assert.deepEqual(result, {timedOut: true, outcomes: [201, null]});
  assert.equal(signal.aborted, true);
  assert.equal(time.cleared, 1);
  assert.match(describeRace(result), /Stopped waiting after 8 seconds/);
  assert.match(describeRace(result), /may already have created/);
  finishLate({status: 409});
  await flush();
  assert.deepEqual(result.outcomes, [201, null]);
  assert.equal(calls, 2);
});

test('synchronous transport failure is reported and timer is cleared', async () => {
  const time = clock();
  const result = await runRace(() => { throw new Error('transport failed'); }, time);
  assert.deepEqual(result.outcomes, ['network-error', 'network-error']);
  assert.equal(time.cleared, 1);
});

for (const mode of ['success', 'timeout', 'failure']) {
  test(`UI ${mode}: recovery link and one experiment per page`, async () => {
    const time = clock();
    let handler, calls = 0;
    const nodes = {
      'race-button': {disabled: false, addEventListener(_, callback) { handler = callback; }},
      'race-form': {action: '/reserve/'},
      'race-result': {textContent: ''},
      'race-refresh': {hidden: true, href: '/?room=focus&day=2026-10-13#booking'},
    };
    attachRace({getElementById: id => nodes[id]}, {
      ...time,
      makeBody: () => 'csrf-and-slot',
      fetchRequest(url, options) {
        calls++;
        assert.equal(url, '/reserve/');
        assert.equal(options.method, 'POST');
        assert.equal(options.credentials, 'same-origin');
        assert.equal(options.body, 'csrf-and-slot');
        assert.ok(options.signal instanceof AbortSignal);
        if (mode === 'timeout') return new Promise(() => {});
        if (mode === 'failure') return Promise.reject(new Error('network'));
        return Promise.resolve({status: calls === 1 ? 201 : 409});
      },
    });
    const first = handler();
    await handler();
    await flush();
    if (mode === 'timeout') time.expire();
    await first;
    await handler();
    assert.equal(calls, 2);
    assert.equal(nodes['race-button'].disabled, true);
    assert.equal(nodes['race-refresh'].hidden, false);
    assert.equal(nodes['race-refresh'].textContent, 'Check your reservations →');
    assert.equal(nodes['race-refresh'].href, '/?room=focus&day=2026-10-13#booking');
    assert.equal(time.cleared, 1);
    assert.doesNotMatch(nodes['race-result'].textContent, /Sending two requests/);
  });
}

test('a fully booked page cannot start a race', async () => {
  let handler;
  attachRace({getElementById: id => id === 'race-button' ? {disabled: true, addEventListener(_, cb) { handler = cb; }} : {}}, {
    fetchRequest() { assert.fail('must not send'); },
  });
  await handler();
  assert.equal(DEADLINE_MS, 8000);
});
