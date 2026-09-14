const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const context = {};
vm.createContext(context);
vm.runInContext(fs.readFileSync('demo/event_transform.js', 'utf8'), context);
const event = {event_id: ' e1 ', customer_id: '1', event_type: 'view', event_time: '2024-02-29T12:00:00Z'};
assert.equal(JSON.parse(context.transform(JSON.stringify(event))).event_id, 'e1');
for (const change of [{event_time: '2026-02-31T12:00:00Z'}, {event_time: 'yesterday'},
                      {event_type: 'unknown'}, {customer_id: null}]) {
  assert.throws(() => context.transform(JSON.stringify({...event, ...change})));
}
assert.throws(() => context.transform('not json'));
console.log('Event contract: leap day, impossible date, missing field, unsupported type and invalid JSON checked');
