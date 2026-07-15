<!-- This file was edited with the assistance of an AI model and requires human review from the contributor. -->
<template>
  <div v-if="tags.length" class="tag-list-cell" data-testid="tag-list-cell">
    <TagBadge v-for="tag in tags" :key="tagKey(tag)" :tag="tag" />
  </div>
</template>

<script>
import TagBadge from "@/components/TagBadge.vue";

export default {
  name: "TagListCell",
  components: {
    TagBadge,
  },
  props: {
    tags: {
      type: Array,
      default: () => [],
    },
  },
  methods: {
    tagKey(tag) {
      if (typeof tag === "string") {
        return `free-text-${tag}`;
      }
      return `managed-${tag.immutable_id || tag.name}`;
    },
  },
};
</script>

<style scoped>
.tag-list-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  align-items: center;
}
</style>
