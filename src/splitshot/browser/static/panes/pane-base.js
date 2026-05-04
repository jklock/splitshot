export function createPaneBase({
  $ = (id) => document.getElementById(id),
  getRoot = () => $("cockpit-root"),
  getExpandedState = () => false,
  setExpandedState = () => {},
  expandedClass = "",
  sectionId = "",
  collapseClasses = [],
  syncUiState = () => {},
  persistUiState = () => {},
  activity = () => {},
  activityName = "pane.expand",
  onExpand = () => {},
  onCollapse = () => {},
} = {}) {
  function root() {
    return getRoot() || $("cockpit-root");
  }

  function section() {
    return sectionId ? $(sectionId) : null;
  }

  function isExpanded() {
    return Boolean(getExpandedState());
  }

  function applyExpandedState(expanded) {
    const nextExpanded = Boolean(expanded);
    const paneRoot = root();
    if (paneRoot && expandedClass) paneRoot.classList.toggle(expandedClass, nextExpanded);
    if (nextExpanded && paneRoot) paneRoot.classList.remove(...collapseClasses);
    const paneSection = section();
    if (paneSection instanceof HTMLElement) paneSection.hidden = !nextExpanded;
    return nextExpanded;
  }

  function setExpanded(expanded, { persistUiState: shouldPersistUiState = true } = {}) {
    const nextExpanded = Boolean(expanded);
    setExpandedState(nextExpanded);
    applyExpandedState(nextExpanded);
    activity(activityName, { expanded: nextExpanded });
    syncUiState();
    if (shouldPersistUiState) persistUiState();
    if (nextExpanded) onExpand(nextExpanded);
    else onCollapse(nextExpanded);
    return nextExpanded;
  }

  return Object.freeze({
    root,
    section,
    isExpanded,
    applyExpandedState,
    setExpanded,
  });
}
