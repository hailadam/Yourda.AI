import test from 'node:test';
import assert from 'node:assert/strict';
import {dailyChange,normalise,money,percent,marketStatusLabel} from '../src/market-utils.js';

test('missing prices never produce fictional quotes',()=>{assert.equal(dailyChange(null),null);assert.equal(dailyChange({price:50}),null);assert.equal(money(null),'—');assert.equal(percent(undefined),'—')});
test('daily percent change uses previous close',()=>{assert.equal(dailyChange({price:104,previous_close:100}),4);assert.equal(dailyChange({price:90,previous_close:100}),-10)});
test('market history keeps valid observations and rejects invalid prices',()=>{const p=normalise([{time:'2026-01-01',close:101,volume:3},{time:'2026-01-02',close:null,volume:5},{time:'2026-01-03',close:-4,volume:5},{time:'2026-01-04',close:112,volume:8}]);assert.deepEqual(p,[{x:'2026-01-01',value:101,volume:3},{x:'2026-01-04',value:112,volume:8}])});
test('do not claim every provider feed is live consolidated',()=>{assert.match(marketStatusLabel('live_iex'),/IEX/);assert.equal(marketStatusLabel(undefined),'Unavailable')});
