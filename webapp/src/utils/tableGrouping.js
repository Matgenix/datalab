import { FilterMatchMode, FilterOperator, FilterService } from "@primevue/core/api";
import { localeComparator, resolveFieldData, sort } from "@primeuix/utils/object";

import { defaultTableRowKey } from "@/utils/tableColumns";

function activeFilters(filters) {
  return Object.fromEntries(
    Object.entries(filters || {}).flatMap(([field, meta]) => {
      if (!meta) return [];
      if (meta?.constraints) {
        const constraints = meta.constraints.filter((constraint) => constraint.value !== null);
        return constraints.length ? [[field, { ...meta, constraints }]] : [];
      }
      return meta?.value !== null ? [[field, meta]] : [];
    }),
  );
}

function matchesConstraint(row, field, constraint, filterLocale) {
  const matchMode = constraint.matchMode || FilterMatchMode.STARTS_WITH;
  const matcher = FilterService.filters[matchMode];
  if (!matcher) throw new Error(`Unknown table filter match mode: ${matchMode}`);
  return matcher(resolveFieldData(row, field), constraint.value, filterLocale);
}

/** Apply the same global and per-column filter model as PrimeVue DataTable. */
export function filterTableRows(rows, filters, globalFilterFields = [], filterLocale) {
  const data = Array.isArray(rows) ? rows : [];
  const active = activeFilters(filters);
  const global = active.global;
  const columns = Object.entries(active).filter(([field]) => field !== "global");

  if (!global && columns.length === 0) return [...data];

  return data.filter((row) => {
    const localMatch = columns.every(([field, meta]) => {
      if (!meta.operator) return matchesConstraint(row, field, meta, filterLocale);
      const results = meta.constraints.map((constraint) =>
        matchesConstraint(row, field, constraint, filterLocale),
      );
      return meta.operator === FilterOperator.OR ? results.some(Boolean) : results.every(Boolean);
    });
    if (!localMatch) return false;
    if (!global) return true;

    const constraint = {
      ...global,
      matchMode: global.matchMode || FilterMatchMode.CONTAINS,
    };
    return globalFilterFields.some((field) =>
      matchesConstraint(row, field, constraint, filterLocale),
    );
  });
}

/** Stable PrimeVue-style multi-column sorting without changing the source array. */
export function sortTableRows(rows, multiSortMeta = []) {
  const data = (Array.isArray(rows) ? rows : []).map((source, index) => ({ source, index }));
  if (!multiSortMeta?.length) return data.map(({ source }) => source);

  const comparer = localeComparator();
  data.sort((left, right) => {
    for (const meta of multiSortMeta) {
      const value1 = resolveFieldData(left.source, meta.field);
      const value2 = resolveFieldData(right.source, meta.field);
      if (value1 === value2) continue;
      return sort(value1, value2, meta.order || 1, comparer, 1);
    }
    return left.index - right.index;
  });
  return data.map(({ source }) => source);
}

function scalarIdentity(value) {
  const type = typeof value;
  if (type === "string" || type === "boolean" || type === "bigint") {
    return JSON.stringify([type, String(value)]);
  }
  if (type === "number") {
    let encoded = String(value);
    if (Number.isNaN(value)) encoded = "NaN";
    else if (Object.is(value, -0)) encoded = "-0";
    return JSON.stringify([type, encoded]);
  }
  throw new Error("Table group and row keys must be scalar values");
}

function groupPathKey(path) {
  return JSON.stringify(path.map(({ descriptorId, identity }) => [descriptorId, identity]));
}

function valuesFor(descriptor, source) {
  const rawValues = descriptor.getValues(source) || [];
  const values = rawValues.length
    ? rawValues.map((value) => ({
        key: value.key,
        label: value.label ?? String(value.key),
        sortValue: value.sortValue ?? value.label ?? value.key,
        isMissing: false,
      }))
    : [
        {
          key: null,
          label: `No ${descriptor.label}`,
          sortValue: null,
          isMissing: true,
        },
      ];

  const deduplicated = new Map();
  for (const value of values) {
    const identity = value.isMissing ? "missing" : `value:${scalarIdentity(value.key)}`;
    if (!deduplicated.has(identity)) deduplicated.set(identity, { ...value, identity });
  }
  return [...deduplicated.values()];
}

function compareGroups(descriptor, left, right) {
  if (left.value.isMissing !== right.value.isMissing) return left.value.isMissing ? 1 : -1;
  const compared = descriptor.compare
    ? descriptor.compare(left.value, right.value)
    : String(left.value.sortValue).localeCompare(String(right.value.sortValue), undefined, {
        numeric: true,
        sensitivity: "base",
      });
  return compared || left.order - right.order;
}

/**
 * Build a nested group tree. A multi-valued descriptor inserts an item into every matching
 * branch, while counts remain unique logical-row counts within each branch.
 */
export function buildGroupTree(rows, descriptors, rowKey = defaultTableRowKey) {
  if (!descriptors?.length) return [];

  let groupOrder = 0;
  const rootMap = new Map();

  function insert(source, logicalKey, logicalIdentity, depth, nodes, path) {
    const descriptor = descriptors[depth];
    for (const value of valuesFor(descriptor, source)) {
      let node = nodes.get(value.identity);
      const nextPath = [...path, { descriptorId: descriptor.id, identity: value.identity }];
      if (!node) {
        node = {
          kind: "group",
          pathKey: groupPathKey(nextPath),
          path: nextPath,
          depth,
          descriptor,
          value,
          count: 0,
          children: [],
          items: [],
          order: groupOrder++,
          childMap: new Map(),
          logicalKeys: new Set(),
          occurrenceKeys: new Set(),
        };
        nodes.set(value.identity, node);
      }

      node.logicalKeys.add(logicalIdentity);
      if (depth < descriptors.length - 1) {
        insert(source, logicalKey, logicalIdentity, depth + 1, node.childMap, nextPath);
      } else if (!node.occurrenceKeys.has(logicalIdentity)) {
        node.occurrenceKeys.add(logicalIdentity);
        node.items.push({
          kind: "item",
          source,
          logicalKey,
          groupPath: node.path,
          displayKey: JSON.stringify(["item", node.pathKey, logicalIdentity]),
        });
      }
    }
  }

  for (const source of Array.isArray(rows) ? rows : []) {
    const logicalKey = rowKey(source);
    const logicalIdentity = scalarIdentity(logicalKey);
    insert(source, logicalKey, logicalIdentity, 0, rootMap, []);
  }

  function finish(nodes, depth) {
    const descriptor = descriptors[depth];
    const result = [...nodes.values()];
    for (const node of result) {
      node.count = node.logicalKeys.size;
      if (node.childMap.size) node.children = finish(node.childMap, depth + 1);
      delete node.childMap;
      delete node.logicalKeys;
      delete node.occurrenceKeys;
    }
    result.sort((left, right) => compareGroups(descriptor, left, right));
    result.forEach((node) => delete node.order);
    return result;
  }

  return finish(rootMap, 0);
}

function pageNumber(pages, pathKey) {
  const page = pages instanceof Map ? pages.get(pathKey) : pages?.[pathKey];
  return Number.isInteger(page) && page >= 0 ? page : 0;
}

function pagination(total, requestedPage, rowsPerPage) {
  const pageCount = Math.ceil(total / rowsPerPage);
  const page = pageCount ? Math.min(requestedPage, pageCount - 1) : 0;
  return {
    page,
    pageCount,
    total,
    first: page * rowsPerPage,
    rows: rowsPerPage,
  };
}

/** Flatten only expanded, currently paged branches into rows suitable for one DataTable. */
export function flattenGroupTree(
  tree,
  { expandedGroupKeys = new Set(), groupPages = new Map(), rootPage = 0, rowsPerPage = 20 } = {},
) {
  const size = Number.isInteger(rowsPerPage) && rowsPerPage > 0 ? rowsPerPage : 20;
  const roots = Array.isArray(tree) ? tree : [];
  const root = pagination(roots.length, rootPage, size);
  const flattened = [];
  const visibleItems = new Map();
  const effectiveGroupPages = new Map();

  function append(group) {
    const entries = group.children.length ? group.children : group.items;
    const groupPage = pagination(entries.length, pageNumber(groupPages, group.pathKey), size);
    effectiveGroupPages.set(group.pathKey, groupPage.page);
    flattened.push({
      __rowKind: "group",
      __displayKey: JSON.stringify(["group", group.pathKey]),
      __groupKey: group.pathKey,
      group,
      groupPage,
    });

    if (!expandedGroupKeys.has(group.pathKey)) return;
    const visibleEntries = entries.slice(groupPage.first, groupPage.first + size);
    if (group.children.length) {
      visibleEntries.forEach(append);
      return;
    }

    for (const occurrence of visibleEntries) {
      const identity = scalarIdentity(occurrence.logicalKey);
      visibleItems.set(identity, occurrence.source);
      flattened.push({
        __rowKind: "item",
        __displayKey: occurrence.displayKey,
        __groupKey: group.pathKey,
        source: occurrence.source,
        logicalKey: occurrence.logicalKey,
        groupPath: occurrence.groupPath,
      });
    }
  }

  roots.slice(root.first, root.first + size).forEach(append);
  return {
    rows: flattened,
    visibleItems: [...visibleItems.values()],
    rootPage: root.page,
    rootTotal: root.total,
    rootPageCount: root.pageCount,
    groupPages: effectiveGroupPages,
  };
}

/** All currently valid group path keys, used to discard stale expansion state after refresh. */
export function collectGroupKeys(tree) {
  const keys = new Set();
  function visit(groups) {
    for (const group of groups || []) {
      keys.add(group.pathKey);
      visit(group.children);
    }
  }
  visit(tree);
  return keys;
}
