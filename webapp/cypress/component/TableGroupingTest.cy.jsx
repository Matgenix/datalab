import { FilterMatchMode, FilterOperator, FilterService } from "@primevue/core/api";

import {
  createCreatorsGroupDescriptor,
  createDateGroupDescriptor,
  createGroupDescriptor,
  createScalarGroupDescriptor,
  createTagsGroupDescriptor,
} from "@/utils/tableGroupDescriptors";
import {
  buildGroupTree,
  collectGroupKeys,
  filterTableRows,
  flattenGroupTree,
  sortTableRows,
} from "@/utils/tableGrouping";
import { defaultTableRowKey } from "@/utils/tableColumns";

const tag = (immutable_id, name) => ({ immutable_id, name });
const creator = (immutable_id, display_name) => ({ immutable_id, display_name });

describe("table grouping utilities", () => {
  const tags = createTagsGroupDescriptor();

  it("resolves the supported logical row identifiers", () => {
    expect(defaultTableRowKey({ item_id: "sample-1" })).to.equal("sample-1");
    expect(defaultTableRowKey({ collection_id: "collection-1" })).to.equal("collection-1");
    expect(defaultTableRowKey({ immutable_id: "immutable-1" })).to.equal("immutable-1");
    expect(defaultTableRowKey({ group_id: "group-1" })).to.equal("group-1");
    expect(defaultTableRowKey({ _id: { $oid: "mongo-1" } })).to.equal("mongo-1");
    expect(() => defaultTableRowKey({ name: "No ID" })).to.throw("stable identifier");
  });

  it("builds nested Cartesian memberships with unique logical counts", () => {
    const rows = [
      {
        item_id: "s1",
        creators: [creator("alice", "Alice"), creator("bob", "Bob")],
        tags: [tag("air", "Air"), tag("cathode", "Cathode")],
      },
      {
        item_id: "s2",
        creators: [creator("alice", "Alice")],
        tags: [tag("cathode", "Cathode")],
      },
      { item_id: "s3", creators: [], tags: [] },
    ];
    const original = structuredClone(rows);
    const tree = buildGroupTree(rows, [createCreatorsGroupDescriptor(), tags]);

    expect(tree.map((group) => group.value.label)).to.deep.equal(["Alice", "Bob", "No Creators"]);
    expect(tree.map((group) => group.count)).to.deep.equal([2, 1, 1]);
    expect(tree[0].children.map((group) => group.value.label)).to.deep.equal(["Air", "Cathode"]);
    expect(tree[0].children.map((group) => group.count)).to.deep.equal([1, 2]);
    expect(tree[1].children.map((group) => group.value.label)).to.deep.equal(["Air", "Cathode"]);
    expect(tree[2].children[0].value.label).to.equal("No Tags");
    expect(tree[0].children[0].items[0].source).to.equal(rows[0]);
    expect(rows).to.deep.equal(original);
  });

  it("deduplicates repeated values while keeping equal labels with distinct keys separate", () => {
    const rows = [
      {
        item_id: "s1",
        tags: [tag("first", "Same"), tag("first", "Same"), tag("second", "Same")],
      },
    ];
    const tree = buildGroupTree(rows, [tags]);

    expect(tree).to.have.length(2);
    expect(tree.map((group) => group.value.key)).to.deep.equal(["first", "second"]);
    expect(tree.map((group) => group.count)).to.deep.equal([1, 1]);
    expect(new Set(tree.map((group) => group.pathKey)).size).to.equal(2);
    expect(tree.every((group) => group.items.length === 1)).to.equal(true);
  });

  it("keeps typed values and the internal missing group collision-safe", () => {
    const value = createScalarGroupDescriptor({ id: "value", label: "Value" });
    const tree = buildGroupTree(
      [
        { item_id: "number", value: 1 },
        { item_id: "string", value: "1" },
        { item_id: "literal", value: "missing" },
        { item_id: "none" },
      ],
      [value],
    );

    expect(tree).to.have.length(4);
    expect(tree.at(-1).value).to.include({ label: "No Value", isMissing: true });
    expect(new Set(tree.map((group) => group.pathKey)).size).to.equal(4);
  });

  it("supports creatorsAndGroups and generic scalar menu entries", () => {
    const creatorDescriptor = createCreatorsGroupDescriptor();
    const values = creatorDescriptor.getValues({
      creatorsAndGroups: [
        { type: "creator", immutable_id: "alice", display_name: "Alice" },
        { type: "group", immutable_id: "lab", display_name: "Lab" },
      ],
    });
    expect(values).to.deep.equal([{ key: "alice", label: "Alice", sortValue: "Alice" }]);

    const status = createGroupDescriptor({ id: "status", label: "Status" });
    expect(status.getValues({ status: "ACTIVE" })).to.deep.equal([
      { key: "ACTIVE", label: "ACTIVE", sortValue: "ACTIVE" },
    ]);
  });

  it("groups stored calendar dates at every supported grain without timezone shifts", () => {
    const source = { date: "2026-05-03T23:30:00-11:00" };
    const expected = {
      day: "2026-05-03",
      week: "2026-04-27",
      month: "2026-05",
      year: "2026",
    };

    for (const [grain, key] of Object.entries(expected)) {
      const descriptor = createDateGroupDescriptor({ grain });
      expect(descriptor.grain).to.equal(grain);
      expect(descriptor.getValues(source)[0].key).to.equal(key);
    }
    expect(createDateGroupDescriptor().getValues({ date: "not-a-date" })).to.deep.equal([]);
    expect(() => createDateGroupDescriptor({ grain: "quarter" })).to.throw("Unsupported");
  });

  it("orders dates newest first and missing dates last", () => {
    const tree = buildGroupTree(
      [
        { item_id: "jan", date: "2026-01-15" },
        { item_id: "apr", date: "2026-04-15" },
        { item_id: "feb", date: "2026-02-15" },
        { item_id: "none" },
      ],
      [createDateGroupDescriptor({ grain: "month" })],
    );
    expect(tree.map((group) => group.value.key)).to.deep.equal([
      "2026-04",
      "2026-02",
      "2026-01",
      null,
    ]);
  });

  it("applies global and AND/OR column filters with registered FilterService matchers", () => {
    FilterService.register("testHasTag", (value, filter) =>
      (value || []).some((entry) => entry.name === filter),
    );
    const rows = [
      { item_id: "s1", name: "Alpha one", status: "ACTIVE", tags: [tag("a", "Air")] },
      { item_id: "s2", name: "Alpha two", status: "FAILED", tags: [tag("b", "Bulk")] },
      { item_id: "s3", name: "Beta", status: "PLANNED", tags: [tag("a", "Air")] },
    ];
    const filters = {
      global: { value: "alpha", matchMode: FilterMatchMode.CONTAINS },
      status: {
        operator: FilterOperator.OR,
        constraints: [
          { value: "ACTIVE", matchMode: FilterMatchMode.EQUALS },
          { value: "PLANNED", matchMode: FilterMatchMode.EQUALS },
        ],
      },
      tags: {
        operator: FilterOperator.AND,
        constraints: [
          { value: "Air", matchMode: "testHasTag" },
          { value: null, matchMode: "testHasTag" },
        ],
      },
    };

    expect(filterTableRows(rows, filters, ["name"]).map((row) => row.item_id)).to.deep.equal([
      "s1",
    ]);
    delete FilterService.filters.testHasTag;
  });

  it("returns all rows for inactive filters and rejects unknown match modes", () => {
    const rows = [{ item_id: "s1", name: "One" }];
    const result = filterTableRows(rows, {
      global: { value: null },
      name: { operator: FilterOperator.AND, constraints: [{ value: null }] },
    });
    expect(result).to.deep.equal(rows);
    expect(result).to.not.equal(rows);
    expect(() =>
      filterTableRows(rows, { name: { value: "x", matchMode: "notRegistered" } }),
    ).to.throw("Unknown table filter match mode");
  });

  it("multi-sorts stably without mutating the input", () => {
    const rows = [
      { item_id: "b", name: "Same", score: 1 },
      { item_id: "a", name: "Same", score: 2 },
      { item_id: "c", name: "Same", score: 2 },
      { item_id: "z", name: "Zulu", score: 9 },
    ];
    const originalOrder = [...rows];
    const result = sortTableRows(rows, [
      { field: "name", order: 1 },
      { field: "score", order: -1 },
    ]);

    expect(result.map((row) => row.item_id)).to.deep.equal(["a", "c", "b", "z"]);
    expect(rows).to.deep.equal(originalOrder);

    const emptyEquivalent = [
      { item_id: "null", primary: null, secondary: 2 },
      { item_id: "undefined", primary: undefined, secondary: 1 },
    ];
    expect(
      sortTableRows(emptyEquivalent, [
        { field: "primary", order: 1 },
        { field: "secondary", order: 1 },
      ]).map((row) => row.item_id),
    ).to.deep.equal(["null", "undefined"]);
  });

  it("flattens only expanded and paged branches", () => {
    const tree = buildGroupTree(
      [
        { item_id: "s1", type: "A", status: "ONE" },
        { item_id: "s2", type: "A", status: "TWO" },
        { item_id: "s3", type: "B", status: "ONE" },
      ],
      [
        createScalarGroupDescriptor({ id: "type", label: "Type" }),
        createScalarGroupDescriptor({ id: "status", label: "Status" }),
      ],
    );
    const typeA = tree[0];
    const typeB = tree[1];
    const statusTwo = typeA.children[1];

    const collapsed = flattenGroupTree(tree, { rowsPerPage: 1 });
    expect(collapsed.rows).to.have.length(1);
    expect(collapsed.rows[0].group).to.equal(typeA);
    expect(collapsed.rootPageCount).to.equal(2);

    const expanded = flattenGroupTree(tree, {
      expandedGroupKeys: new Set([typeA.pathKey, statusTwo.pathKey]),
      groupPages: new Map([[typeA.pathKey, 1]]),
      rowsPerPage: 1,
    });
    expect(expanded.rows.map((row) => row.__rowKind)).to.deep.equal(["group", "group", "item"]);
    expect(expanded.rows[1].group).to.equal(statusTwo);
    expect(expanded.rows[2].source.item_id).to.equal("s2");

    const secondRoot = flattenGroupTree(tree, { rootPage: 1, rowsPerPage: 1 });
    expect(secondRoot.rows[0].group).to.equal(typeB);
  });

  it("clamps stale pages and exposes pager metadata on group sentinels", () => {
    const tree = buildGroupTree(
      [
        { item_id: "s1", status: "ACTIVE" },
        { item_id: "s2", status: "ACTIVE" },
      ],
      [createScalarGroupDescriptor({ id: "status", label: "Status" })],
    );
    const group = tree[0];
    const result = flattenGroupTree(tree, {
      rootPage: 12,
      expandedGroupKeys: new Set([group.pathKey]),
      groupPages: new Map([[group.pathKey, 12]]),
      rowsPerPage: 1,
    });

    expect(result.rootPage).to.equal(0);
    expect(result.rows[0].groupPage).to.deep.include({ page: 1, pageCount: 2, total: 2 });
    expect(result.rows[1].source.item_id).to.equal("s2");
    expect(result.groupPages.get(group.pathKey)).to.equal(1);
  });

  it("gives duplicate occurrences distinct display keys and deduplicates visible selection", () => {
    const tree = buildGroupTree(
      [{ item_id: "s1", tags: [tag("air", "Air"), tag("bulk", "Bulk")] }],
      [tags],
    );
    const expanded = new Set(tree.map((group) => group.pathKey));
    const result = flattenGroupTree(tree, {
      expandedGroupKeys: expanded,
      rowsPerPage: 20,
    });
    const occurrences = result.rows.filter((row) => row.__rowKind === "item");

    expect(occurrences).to.have.length(2);
    expect(new Set(occurrences.map((row) => row.__displayKey)).size).to.equal(2);
    expect(occurrences.map((row) => row.logicalKey)).to.deep.equal(["s1", "s1"]);
    expect(result.visibleItems).to.deep.equal([tree[0].items[0].source]);
    expect(collectGroupKeys(tree)).to.deep.equal(expanded);
  });
});
