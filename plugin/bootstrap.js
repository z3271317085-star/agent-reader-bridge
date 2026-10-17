var bridgeScope;
var bridgeTimer;
var lastReader = null;
var lastSignature = '';
var revision = 0;
var ENDPOINT = '/agent-reader/context';

function install() {}
function uninstall() {}

function chooseCurrentReader() {
  const readers = Zotero.Reader._readers || [];
  // Poll only foreground Zotero windows to remember detached-window focus.
  for (const reader of readers) {
    if (!reader.tabID && reader._window?.document?.hasFocus()) {
      lastReader = reader;
      return reader;
    }
  }
  const wins = Zotero.getMainWindows ? Zotero.getMainWindows() : [Zotero.getMainWindow()];
  const focused = wins.find(w => w?.document?.hasFocus());
  if (focused) {
    lastReader = bridgeScope.AgentReaderAdapter.chooseReader(readers, focused.Zotero_Tabs?.selectedID, null);
    return lastReader;
  }
  // While Codex is foreground, keep the last reading window, but never a closed one.
  const previous = bridgeScope.AgentReaderAdapter.chooseReader(readers, null, lastReader);
  if (previous) {
    if (previous.tabID) {
      lastReader = bridgeScope.AgentReaderAdapter.chooseReader(readers, previous._window?.Zotero_Tabs?.selectedID, null);
      return lastReader;
    }
    return previous;
  }
  const win = Zotero.getMainWindow();
  lastReader = bridgeScope.AgentReaderAdapter.chooseReader(readers, win?.Zotero_Tabs?.selectedID, null);
  return lastReader;
}

async function context() {
  const reader = chooseCurrentReader();
  if (!reader) return {error: 'no_active_reader', message: 'Open a PDF reading tab in Zotero.'};
  if (reader.type !== 'pdf') return {error: 'unsupported_document_type', message: 'Only standard PDF reading is supported.'};
  const state = bridgeScope.AgentReaderAdapter.extractState(reader);
  const attachment = Zotero.Items.get(reader.itemID);
  if (!attachment) return {error: 'attachment_unavailable'};
  const path = await attachment.getFilePathAsync();
  if (!path) return {error: 'attachment_not_local'};
  const parent = attachment.parentItemID ? Zotero.Items.get(attachment.parentItemID) : null;
  const info = {
    document_id: `${attachment.libraryID}:${attachment.key}`,
    reader_id: reader.tabID || `window:${reader.itemID}`,
    title: (parent || attachment).getField('title'),
    zotero_version: Zotero.version,
    path,
    ...state,
  };
  const signature = JSON.stringify(info);
  if (signature !== lastSignature) { revision++; lastSignature = signature; }
  return {...info, revision, captured_at: new Date().toISOString()};
}

async function startup(data, reason) {
  await Zotero.initializationPromise;
  bridgeScope = {Zotero};
  Services.scriptloader.loadSubScript(data.rootURI + 'adapter.js', bridgeScope);
  Services.scriptloader.loadSubScript(data.rootURI + 'secret.js', bridgeScope);
  Zotero.Server.Endpoints[ENDPOINT] = function () {};
  Zotero.Server.Endpoints[ENDPOINT].prototype = {
    supportedMethods: ['GET'],
    supportedDataTypes: [],
    permitBookmarklet: false,
    allowRequestsFromUnsafeWebContent: false,
    async init(request) {
      const respond = (code, body) => [code, {'Content-Type': 'application/json', 'Cache-Control': 'no-store'}, JSON.stringify(body)];
      if (request.headers.authorization !== `Bearer ${bridgeScope.AGENT_READER_TOKEN}`) {
        return respond(401, {error: 'unauthorized'});
      }
      try { return respond(200, await context()); }
      catch (e) {
        Zotero.logError(e);
        return respond(503, {error: 'reader_adapter_unavailable', message: String(e.message)});
      }
    },
  };
  bridgeTimer = setInterval(() => {
    try { chooseCurrentReader(); } catch (e) { Zotero.logError(e); }
  }, 300);
}

function shutdown(data, reason) {
  if (bridgeTimer) clearInterval(bridgeTimer);
  delete Zotero.Server.Endpoints[ENDPOINT];
  lastReader = null;
  bridgeScope = null;
}
