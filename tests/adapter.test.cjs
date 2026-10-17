const test = require('node:test');
const assert = require('node:assert/strict');
const { extractState, chooseReader } = require('../plugin/adapter.js');

function reader(id, index = 0, ranges = []) {
  return {tabID: id, _internalReader: {
    _lastViewPrimary: true,
    _state: {primaryViewState: {pageIndex: index}, pageLabels: ['i', '1', '2']},
    _lastView: {_selectionRanges: ranges}
  }};
}
test('physical page differs from printed label, cross-page selection retained', () => {
  const r = reader('a', 1, [{text: 'first', position: {pageIndex: 1, rects: [[1,2,3,4]]}},
    {text: 'second', position: {pageIndex: 2, rects: []}}]);
  const state = extractState(r);
  assert.equal(state.page, 2);
  assert.equal(state.page_label, '1');
  assert.equal(state.selection.text, 'first\nsecond');
  assert.deepEqual(state.selection.pages, [2, 3]);
});
test('collapsed selection clears old text', () => {
  assert.equal(extractState(reader('a', 0, [{collapsed:true,text:'old'}])).selection.text, '');
});
test('selection arrays from another privilege realm are copied before callbacks', () => {
  const ranges = [{text:'selected evidence',position:{pageIndex:1,rects:[[1,2,3,4]]}}];
  Object.defineProperty(ranges,'map',{value:()=>{throw Error('Permission denied to pass object to privileged code');}});
  const state = extractState(reader('a',1,ranges));
  assert.equal(state.selection.text,'selected evidence');
  assert.deepEqual(state.selection.pages,[2]);
});
test('secondary view supplies page and selection', () => {
  const r = reader('a');
  r._internalReader._lastViewPrimary = false;
  r._internalReader._state.secondaryViewState = {pageIndex: 2};
  assert.equal(extractState(r).page, 3);
});
test('unknown reader layout fails instead of returning page one', () => {
  assert.throws(() => extractState({_internalReader: {_state:{}}}), /unsupported_reader_state/);
});
test('selected tab wins and closed last reader is not reused', () => {
  const a = reader('a'), b = reader('b');
  assert.equal(chooseReader([a,b], 'b', a), b);
  assert.equal(chooseReader([b], null, a), null);
  assert.equal(chooseReader([a,b], null, a), a);
});
