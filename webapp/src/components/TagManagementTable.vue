<template>
  <DynamicDataTable
    :columns="tagColumns"
    :data="tags"
    data-type="tags"
    :global-filter-fields="['name', 'description']"
    :show-buttons="true"
    :edit-page-route-prefix="'tags'"
    @open-create-tag-modal="openCreateModal"
    @edit-tag="openEditModal"
  />
  <TagFormModal
    v-model="tagModalIsOpen"
    :tag="editingTag"
    @tag-created="getTags"
    @tag-updated="getTags"
  />
</template>

<script>
import DynamicDataTable from "@/components/DynamicDataTable";
import TagFormModal from "@/components/TagFormModal.vue";
import { getTags } from "@/server_fetch_utils.js";

export default {
  name: "TagManagementTable",
  components: { DynamicDataTable, TagFormModal },
  data() {
    return {
      tagModalIsOpen: false,
      editingTag: null,
      tagColumns: [
        {
          field: "name",
          header: "Tag",
          body: "TagBadge",
          bodyConfig: { tag: "tag" },
          label: "Tag",
          filter: true,
        },
        {
          field: "description",
          header: "Description",
          label: "Description",
          filter: true,
        },
        {
          field: "creatorsAndGroups",
          header: "Creators",
          body: "Creators",
          filter: true,
          label: "Creators",
        },
        {
          field: "actions",
          header: "Actions",
          body: "TagActionsCell",
          bodyConfig: { tag: "tag" },
        },
      ],
    };
  },
  computed: {
    tags() {
      if (!this.$store.state.tag_list) {
        return null;
      }
      // Build the `creatorsAndGroups` virtual field the Creators column's filter relies on
      // (same shape as SampleTable), merging creators and groups with a discriminating `type`.
      return this.$store.state.tag_list.map((tag) => ({
        ...tag,
        creatorsAndGroups: [
          ...(tag.creators || []).map((c) => ({ ...c, type: "creator" })),
          ...(tag.groups || []).map((g) => ({ ...g, type: "group" })),
        ],
      }));
    },
  },
  created() {
    this.getTags();
  },
  methods: {
    getTags() {
      getTags();
    },
    openCreateModal() {
      this.editingTag = null;
      this.tagModalIsOpen = true;
    },
    openEditModal(tag) {
      this.editingTag = tag;
      this.tagModalIsOpen = true;
    },
  },
};
</script>
