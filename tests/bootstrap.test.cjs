const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

test('Zotero plain proxy headers enforce authentication and return no-reader error', async () => {
  const Zotero = {
    initializationPromise: Promise.resolve(), Reader: {_readers: []},
    Server: {Endpoints: {}}, getMainWindow: () => null, logError: () => {},
  };
  const scope = {Zotero, console, setInterval: () => 1, clearInterval: () => {},
    Services: {scriptloader: {loadSubScript(url, target) {
      if (url.endsWith('adapter.js')) vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../plugin/adapter.js'),'utf8'), target);
      else target.AGENT_READER_TOKEN = 'test-token';
    }}}};
  vm.createContext(scope);
  vm.runInContext('delete globalThis.console', scope);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../plugin/bootstrap.js'),'utf8'), scope);
  await scope.startup({rootURI:'file:///plugin/'}, 0);
  const endpoint = new Zotero.Server.Endpoints['/agent-reader/context']();
  assert.equal((await endpoint.init({headers:{}}))[0], 401);
  const result = await endpoint.init({headers:{authorization:'Bearer test-token'}});
  assert.equal(result[0],200);
  assert.equal(JSON.parse(result[2]).error,'no_active_reader');
  scope.shutdown({},0);
  assert.equal(Zotero.Server.Endpoints['/agent-reader/context'], undefined);
});
