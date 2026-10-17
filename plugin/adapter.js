/* Zotero 10 adapter. Private reader fields are deliberately isolated here. */
var AgentReaderAdapter = (() => {
  function chooseReader(readers, selectedTabID, previous) {
    const alive = readers.filter(r => !r._isTabClosed && !r._window?.closed);
    if (selectedTabID !== null && selectedTabID !== undefined) {
      return alive.find(r => r.tabID === selectedTabID) || null;
    }
    return alive.includes(previous) ? previous : null;
  }

  function extractState(reader) {
    const internal = reader?._internalReader;
    const primary = internal?._lastViewPrimary !== false;
    const state = internal?._state;
    const viewState = state?.[primary ? 'primaryViewState' : 'secondaryViewState'];
    const index = viewState?.pageIndex;
    if (!Number.isInteger(index) || index < 0) throw new Error('unsupported_reader_state');
    const view = internal._lastView;
    const rawRanges = view?._selectionRanges;
    // Reading mode is a separate view implementation. Never claim no selection
    // when that implementation is not supported by this adapter.
    if (!Array.isArray(rawRanges)) throw new Error('unsupported_selection_view_use_standard_pdf_mode');
    // The PDF iframe is a different Gecko privilege realm. Do not invoke its
    // Array.map with a privileged callback. Copy data before processing it,
    // matching Zotero's own onChangeViewState boundary handling.
    const ranges = JSON.parse(JSON.stringify(rawRanges));
    const selected = ranges.length && !ranges[0].collapsed ? ranges : [];
    const text = selected.map(r => r.text || '').join('\n');
    const positions = selected.map(r => r.position).filter(Boolean)
      .map(p => ({page: p.pageIndex + 1, rects: p.rects || []}));
    return {
      page: index + 1,
      page_label: String(state.pageLabels?.[index] ?? index + 1),
      view: primary ? 'primary' : 'secondary',
      selection: {
        text: text.slice(0, 50000),
        truncated: text.length > 50000,
        pages: [...new Set(positions.map(p => p.page))],
        positions,
      },
    };
  }
  return {chooseReader, extractState};
})();
if (typeof module !== 'undefined') module.exports = AgentReaderAdapter;
