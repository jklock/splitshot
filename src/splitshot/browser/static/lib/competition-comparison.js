function normalizedKey(value) {
  return String(value || "").trim().toLocaleLowerCase();
}

function finiteResult(value) {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function competitionRank(sorted, selectedIndex, resultKey) {
  if (selectedIndex < 0) return null;
  const selectedValue = sorted[selectedIndex][resultKey];
  const firstEqualIndex = sorted.findIndex((item) => item[resultKey] === selectedValue);
  return firstEqualIndex + 1;
}

function buildCohort(items, selectedNameKey, resultKey, ascending) {
  const sorted = items
    .filter((item) => finiteResult(item[resultKey]) !== null)
    .map((item) => ({ ...item, [resultKey]: finiteResult(item[resultKey]) }))
    .sort((left, right) => ascending
      ? left[resultKey] - right[resultKey]
      : right[resultKey] - left[resultKey]);
  const selectedIndex = sorted.findIndex((item) => normalizedKey(item.name) === selectedNameKey);
  const current = selectedIndex >= 0 ? sorted[selectedIndex] : null;
  const leader = sorted[0] || null;
  const rank = competitionRank(sorted, selectedIndex, resultKey);
  const count = sorted.length;
  const percentile = rank === null || count === 0
    ? null
    : Number((((count - rank + 1) / count) * 100).toFixed(1));
  const gap = current && leader
    ? Number((ascending
      ? current[resultKey] - leader[resultKey]
      : leader[resultKey] - current[resultKey]).toFixed(4))
    : null;
  return { items: sorted, current, leader, rank, place: rank, count, percentile, gap };
}

export function buildCompetitionComparison({ scoring = {}, importedStage = {}, competitors = [] } = {}) {
  const matchType = normalizedKey(scoring.match_type || importedStage.match_type);
  const ruleset = normalizedKey(scoring.ruleset);
  const idpa = matchType === "idpa" || ruleset.includes("idpa");
  const resultKey = idpa ? "final_time" : "hit_factor";
  const ascending = idpa;
  const identity = {
    name: String(scoring.competitor_name || importedStage.competitor_name || "").trim(),
    division: String(scoring.division || importedStage.division || "").trim(),
    classification: String(scoring.classification || importedStage.classification || "").trim(),
  };
  const selectedNameKey = normalizedKey(identity.name);
  const selected = {
    ...importedStage,
    name: identity.name,
    division: identity.division,
    classification: identity.classification,
  };
  const all = [selected, ...competitors]
    .filter((item) => String(item?.name || item?.competitor_name || "").trim())
    .map((item) => ({
      ...item,
      name: String(item.name || item.competitor_name || "").trim(),
      division: String(item.division || "").trim(),
      classification: String(item.classification || "").trim(),
    }));
  const divisionKey = normalizedKey(identity.division);
  const classificationKey = normalizedKey(identity.classification);
  const build = (items) => buildCohort(items, selectedNameKey, resultKey, ascending);
  return {
    sport: idpa ? "idpa" : "hit_factor",
    resultKey,
    ascending,
    identity,
    overall: build(all),
    division: divisionKey ? build(all.filter((item) => normalizedKey(item.division) === divisionKey)) : build([]),
    classification: classificationKey
      ? build(all.filter((item) => normalizedKey(item.classification) === classificationKey))
      : build([]),
    divisionClassification: divisionKey && classificationKey
      ? build(all.filter((item) => normalizedKey(item.division) === divisionKey && normalizedKey(item.classification) === classificationKey))
      : build([]),
  };
}

function positivePlace(value) {
  const numeric = finiteResult(value);
  return numeric !== null && numeric > 0 ? numeric : null;
}

function buildStandingsCohort(items, selectedNameKey) {
  const sorted = items
    .filter((item) => positivePlace(item.place) !== null)
    .map((item) => ({ ...item, place: positivePlace(item.place) }))
    .sort((left, right) => left.place - right.place);
  const selectedIndex = sorted.findIndex((item) => normalizedKey(item.name) === selectedNameKey);
  if (selectedIndex < 0) return { items: sorted, current: null, rank: null, place: null, count: sorted.length };
  const selectedPlace = sorted[selectedIndex].place;
  const rank = sorted.findIndex((item) => item.place === selectedPlace) + 1;
  return { items: sorted, current: sorted[selectedIndex], rank, place: rank, count: sorted.length };
}

export function buildFinalStandingsComparison({ scoring = {}, importedStage = {}, competitors = [] } = {}) {
  const identity = {
    name: String(scoring.competitor_name || importedStage.competitor_name || "").trim(),
    division: String(scoring.division || importedStage.division || "").trim(),
    classification: String(scoring.classification || importedStage.classification || "").trim(),
  };
  const selectedNameKey = normalizedKey(identity.name);
  const selected = { ...importedStage, ...identity, place: importedStage.competitor_place ?? importedStage.place };
  const deduplicated = new Map();
  [selected, ...competitors].forEach((item) => {
    const name = String(item?.name || item?.competitor_name || "").trim();
    const key = normalizedKey(name);
    if (!key || deduplicated.has(key)) return;
    deduplicated.set(key, {
      ...item,
      name,
      division: String(item.division || "").trim(),
      classification: String(item.classification || "").trim(),
      place: item.place ?? item.competitor_place,
    });
  });
  const all = [...deduplicated.values()];
  const divisionKey = normalizedKey(identity.division);
  const classificationKey = normalizedKey(identity.classification);
  const build = (items) => buildStandingsCohort(items, selectedNameKey);
  return {
    identity,
    overall: build(all),
    division: divisionKey ? build(all.filter((item) => normalizedKey(item.division) === divisionKey)) : build([]),
    classification: classificationKey ? build(all.filter((item) => normalizedKey(item.classification) === classificationKey)) : build([]),
    divisionClassification: divisionKey && classificationKey
      ? build(all.filter((item) => normalizedKey(item.division) === divisionKey && normalizedKey(item.classification) === classificationKey))
      : build([]),
  };
}
