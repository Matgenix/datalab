<template>
  <StyledTooltip>
    <template #anchor>
      <span
        class="badge badge-pill tag-badge"
        :class="isManaged ? 'managed-tag' : 'free-text-tag'"
        :style="tagStyle"
      >
        {{ tagName }}
      </span>
    </template>
    <template #content>
      {{ tagTooltip }}
    </template>
  </StyledTooltip>
</template>

<script>
import { readableTextColor } from "@/field_utils.js";
import StyledTooltip from "@/components/StyledTooltip.vue";

export default {
  name: "TagBadge",
  components: {
    StyledTooltip,
  },
  props: {
    // A tag is either a free-text string or a reference object
    // `{ type: "tags", immutable_id, name, color, description }`.
    tag: {
      type: [Object, String],
      required: true,
    },
    // Force the managed/free-text styling instead of inferring it from the
    // tag's `immutable_id`. Useful for previewing a managed tag that has not
    // been persisted yet (and so has no id). When null, the styling is
    // inferred from the tag itself.
    managed: {
      type: Boolean,
      default: null,
    },
  },
  computed: {
    isManaged() {
      if (this.managed !== null) {
        return this.managed;
      }
      return typeof this.tag !== "string" && Boolean(this.tag.immutable_id);
    },
    tagName() {
      return typeof this.tag === "string" ? this.tag : this.tag.name;
    },
    tagTooltip() {
      // Prefer the tag's description; otherwise fall back to a simple type hint.
      if (typeof this.tag === "string") {
        return "Free-text tag";
      }
      return this.tag.description || "Managed tag";
    },
    tagColor() {
      return typeof this.tag !== "string" && this.tag.color ? this.tag.color : null;
    },
    tagStyle() {
      // When a tag has a color, use it as the badge background with a readable
      // text color; otherwise fall back to the managed/free-text CSS classes.
      const color = this.tagColor;
      return color ? { backgroundColor: color, color: readableTextColor(color) } : {};
    },
  },
};
</script>

<style scoped>
.tag-badge {
  font-size: 0.85em;
  font-weight: 500;
}
.managed-tag {
  background-color: #d1e7dd;
  color: #0f5132;
}
.free-text-tag {
  background-color: #e2e3e5;
  color: #41464b;
  font-style: italic;
}
</style>
