<template>
  <div>
    <div class="mb-3">
      <button type="button" data-testid="show-flat" @click="mode = 'flat'">Flat</button>
      <button type="button" data-testid="group-by-tags" @click="mode = 'tags'">
        Group by tags
      </button>
      <button type="button" data-testid="show-pagination" @click="paginationMode = true">
        Pagination example
      </button>
      <button type="button" data-testid="group-by-tags-status" @click="mode = 'nested'">
        Group by tags, then status
      </button>
    </div>

    <DynamicDataTable
      :columns="columns"
      :data="tableRows"
      data-type="groupingExample"
      :global-filter-fields="['item_id', 'name', 'status', 'tagsList']"
      :group-by="groupBy"
      :row-key="rowKey"
      test-id="grouping-example-table"
    />
  </div>
</template>

<script>
import DynamicDataTable from "@/components/DynamicDataTable.vue";
import {
  createScalarGroupDescriptor,
  createTagsGroupDescriptor,
} from "@/utils/tableGroupDescriptors";

const tags = createTagsGroupDescriptor();
const status = createScalarGroupDescriptor({ id: "status", label: "Status" });

export default {
  name: "DynamicDataTableGroupingExample",
  components: { DynamicDataTable },
  data() {
    return {
      mode: "flat",
      paginationMode: false,
      columns: [
        { field: "item_id", header: "ID" },
        { field: "name", header: "Name" },
        { field: "status", header: "Status" },
        { field: "tagsList", header: "Tags" },
      ],
      rows: [
        {
          item_id: "item-1",
          name: "Alpha",
          status: "Active",
          tags: [
            { immutable_id: "red", name: "Red" },
            { immutable_id: "blue", name: "Blue" },
          ],
          tagsList: "Red, Blue",
        },
        {
          item_id: "item-2",
          name: "Beta",
          status: "Active",
          tags: [{ immutable_id: "red", name: "Red" }],
          tagsList: "Red",
        },
        {
          item_id: "item-3",
          name: "Gamma",
          status: "Archived",
          tags: [{ immutable_id: "blue", name: "Blue" }],
          tagsList: "Blue",
        },
        {
          item_id: "item-4",
          name: "Delta",
          status: "Archived",
          tags: [],
          tagsList: "",
        },
        {
          item_id: "item-5",
          name: "Epsilon",
          status: "Active",
          tags: [{ immutable_id: "red", name: "Red" }],
          tagsList: "Red",
        },
        {
          item_id: "item-6",
          name: "Zeta",
          status: "Active",
          tags: [{ immutable_id: "red", name: "Red" }],
          tagsList: "Red",
        },
        {
          item_id: "item-7",
          name: "Eta",
          status: "Active",
          tags: [{ immutable_id: "red", name: "Red" }],
          tagsList: "Red",
        },
        {
          item_id: "item-8",
          name: "Theta",
          status: "Active",
          tags: [{ immutable_id: "red", name: "Red" }],
          tagsList: "Red",
        },
        {
          item_id: "item-9",
          name: "Iota",
          status: "Active",
          tags: [{ immutable_id: "red", name: "Red" }],
          tagsList: "Red",
        },
        {
          item_id: "item-10",
          name: "Kappa",
          status: "Active",
          tags: [{ immutable_id: "red", name: "Red" }],
          tagsList: "Red",
        },
        {
          item_id: "item-11",
          name: "Lambda",
          status: "Active",
          tags: [{ immutable_id: "green", name: "Green" }],
          tagsList: "Green",
        },
        {
          item_id: "item-12",
          name: "Mu",
          status: "Archived",
          tags: [{ immutable_id: "green", name: "Green" }],
          tagsList: "Green",
        },
        {
          item_id: "item-13",
          name: "Nu",
          status: "Active",
          tags: [{ immutable_id: "green", name: "Green" }],
          tagsList: "Green",
        },
        {
          item_id: "item-14",
          name: "Xi",
          status: "Archived",
          tags: [{ immutable_id: "yellow", name: "Yellow" }],
          tagsList: "Yellow",
        },
        {
          item_id: "item-15",
          name: "Omicron",
          status: "Active",
          tags: [{ immutable_id: "teal", name: "Teal" }],
          tagsList: "Teal",
        },
        {
          item_id: "item-16",
          name: "Pi",
          status: "Archived",
          tags: [{ immutable_id: "teal", name: "Teal" }],
          tagsList: "Teal",
        },
      ],
    };
  },
  computed: {
    tableRows() {
      return this.paginationMode ? this.rows : this.rows.slice(0, 4);
    },
    groupBy() {
      if (this.mode === "tags") return [tags];
      if (this.mode === "nested") return [tags, status];
      return [];
    },
  },
  methods: {
    rowKey(item) {
      return item.item_id;
    },
  },
};
</script>
