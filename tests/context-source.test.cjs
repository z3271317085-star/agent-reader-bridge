const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

test('switching tabs immediately before polling returns current tab, not cached tab', () => {
  const win = {closed:false, document:{hasFocus:()=>false}, Zotero_Tabs:{selectedID:'b'}};
  const a = {tabID:'a',_window:win}, b = {tabID:'b',_window:win};
  const scope = {Zotero:{Reader:{_readers:[a,b]},getMainWindow:()=>win,getMainWindows:()=>[win]}};
  vm.createContext(scope);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../plugin/bootstrap.js'),'utf8'),scope);
  scope.bridgeScope = {AgentReaderAdapter:require('../plugin/adapter.js')};
  scope.lastReader = a;
  assert.equal(scope.chooseCurrentReader(),b);
  win.Zotero_Tabs.selectedID = 'zotero-pane';
  assert.equal(scope.chooseCurrentReader(),null);
});
