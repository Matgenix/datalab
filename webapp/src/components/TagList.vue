<template>
  <div class="tag-list d-flex flex-wrap align-items-center">
    <TagBadge v-for="(tag, index) in tags" :key="tagKey(tag, index)" :tag="tag" />
    <span v-if="!tags || tags.length === 0" class="text-muted small">No tags</span>
  </div>
</template>

<script>
import TagBadge from "@/components/TagBadge.vue";

export default {
  components: {
    TagBadge,
  },
  props: {
    // Each tag is either a free-text string or a reference object
    // `{ type: "tags", immutable_id, name, color }`.
    tags: {
      type: Array,
      default: () => [],
    },
  },
  methods: {
    tagKey(tag, index) {
      if (typeof tag === "string") {
        return `free-text-${tag}`;
      }
      return tag.immutable_id || `tag-${index}`;
    },
  },
};
</script>

<style scoped>
/* Layout uses Bootstrap d-flex utilities; only the gap stays as CSS since
   Bootstrap 4 has no gap utilities. */
.tag-list {
  gap: 0.3rem;
}
</style>
