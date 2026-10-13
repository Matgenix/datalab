<template>
  <div>
    <div class="mb-3">
      <button type="button" data-testid="show-flat" @click="mode = 'flat'">Flat</button>
      <button type="button" data-testid="group-by-tags" @click="mode = 'tags'">
        Group by tags
      </button>
      <button type="button" data-testid="group-by-tags-status" @click="mode = 'nested'">
        Group by tags, then status
      </button>
    </div>

    <DynamicDataTable
      :columns="columns"
      :data="rows"
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
      ],
    };
  },
  computed: {
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
