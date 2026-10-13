<template>
  <div
    data-testid="group-header"
    class="data-table-group-header d-flex align-items-center w-100"
    :style="{ paddingLeft: `${depth * 1.25}rem` }"
  >
    <button
      type="button"
      data-testid="group-toggle"
      class="btn btn-link btn-sm p-0 mr-2 text-body group-toggle"
      :aria-label="`${expanded ? 'Collapse' : 'Expand'} ${label}`"
      :aria-expanded="expanded"
      @click.stop="$emit('toggle')"
    >
      <span aria-hidden="true">{{ expanded ? "▾" : "▸" }}</span>
    </button>

    <span class="font-weight-bold">{{ label }}</span>
    <span class="badge badge-secondary badge-pill ml-2">{{ count }}</span>

    <div
      v-if="pageCount > 1"
      data-testid="group-pager"
      class="group-pager d-flex align-items-center ml-auto"
    >
      <button
        type="button"
        class="btn btn-link btn-sm py-0"
        aria-label="Previous group page"
        :disabled="page === 0"
        @click.stop="$emit('page', page - 1)"
      >
        ‹
      </button>
      <span class="small text-muted">{{ page + 1 }} / {{ pageCount }}</span>
      <button
        type="button"
        class="btn btn-link btn-sm py-0"
        aria-label="Next group page"
        :disabled="page >= pageCount - 1"
        @click.stop="$emit('page', page + 1)"
      >
        ›
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: "DataTableGroupHeader",
  props: {
    label: { type: String, required: true },
    count: { type: Number, required: true },
    depth: { type: Number, default: 0 },
    expanded: { type: Boolean, default: false },
    page: { type: Number, default: 0 },
    pageCount: { type: Number, default: 1 },
  },
  emits: ["toggle", "page"],
};
</script>

<style scoped>
.group-toggle {
  width: 1rem;
  line-height: 1;
  text-decoration: none;
}

.group-pager button:disabled {
  opacity: 0.35;
}
</style>
