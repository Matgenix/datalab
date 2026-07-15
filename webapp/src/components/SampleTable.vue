<!-- This file was edited with the assistance of an AI model and requires human review from the contributor. -->
<template>
  <DynamicDataTable
    :columns="sampleColumns"
    :data="samples"
    :data-type="'samples'"
    :global-filter-fields="sampleGlobalFilterFields"
  />
</template>

<script>
import DynamicDataTable from "@/components/DynamicDataTable";
import { ENABLE_TAGS } from "@/resources.js";
import { getSampleList } from "@/server_fetch_utils.js";

export default {
  components: { DynamicDataTable },
  data() {
    return {
      baseSampleColumns: [
        {
          field: "item_id",
          header: "ID",
          body: "FormattedItemName",
          filter: true,
          label: "ID",
        },
        { field: "type", header: "Type", filter: true, label: "Type" },
        { field: "status", header: "Status", body: "FormattedItemStatus", filter: true },
        { field: "name", header: "Name", label: "Sample name" },
        {
          field: "chemform",
          header: "Formula",
          body: "ChemicalFormula",
          label: "Formula",
        },
        { field: "date", header: "Date", label: "Date", filter: true },
        {
          field: "collections",
          header: "Collections",
          body: "CollectionList",
          filter: true,
          label: "Collections",
        },
        {
          field: "creatorsAndGroups",
          header: "Creators",
          body: "Creators",
          filter: true,
          label: "Creators",
        },
        {
          field: "blocks",
          header: "",
          body: "BlocksIconCounter",
          icon: ["fa", "cubes"],
          filter: true,
          label: "Blocks",
        },
        {
          field: "nfiles",
          header: "",
          body: "FilesIconCounter",
          icon: ["fa", "file"],
          label: "Files",
        },
      ],
    };
  },
  computed: {
    enableTags() {
      return ENABLE_TAGS;
    },
    sampleColumns() {
      const columns = [...this.baseSampleColumns];
      if (this.enableTags) {
        const insertBeforeBlocks = columns.findIndex((column) => column.field === "blocks");
        columns.splice(insertBeforeBlocks, 0, {
          field: "tags",
          header: "Tags",
          body: "TagList",
          filter: true,
          label: "Tags",
        });
      }
      return columns;
    },
    sampleGlobalFilterFields() {
      const fields = [
        "item_id",
        "name",
        "refcode",
        "chemform",
        "creatorsList",
        "blocks",
        "characteristic_chemical_formula",
      ];
      if (this.enableTags) {
        fields.push("tagsList");
      }
      return fields;
    },
    samples() {
      if (!this.$store.state.sample_list) {
        return null;
      }
      return this.$store.state.sample_list.map((sample) => {
        return {
          ...sample,
          creatorsAndGroups: [
            ...(sample.creators || []).map((c) => ({ ...c, type: "creator" })),
            ...(sample.groups || []).map((g) => ({ ...g, type: "group" })),
          ],
          collectionsList: sample.collections
            .map((collection) => collection.collection_id)
            .join(", "),
          creatorsList: sample.creators.map((creator) => creator.display_name).join(", "),
          tagsList: (sample.tags || [])
            .map((tag) => (typeof tag === "string" ? tag : tag.name))
            .filter(Boolean)
            .join(", "),
        };
      });
    },
  },
  mounted() {
    this.getSamples();
  },
  methods: {
    getSamples() {
      getSampleList();
    },
  },
};
</script>
