<template>
  <div class="asd-panel" @click.stop>
    <div class="asd-col">
      <span class="asd-col__title">Filters</span>
      <button
        v-for="f in quickFilters"
        :key="f.id"
        type="button"
        class="asd-row"
        @click="toggleFilter(f.id)"
      >
        <font-awesome-icon
          icon="check"
          class="asd-row__check"
          :class="{ 'asd-row__check--hidden': !activeFilters.includes(f.id) }"
        />
        <span>{{ f.label }}</span>
      </button>
      <div class="asd-divider"></div>
      <button type="button" class="asd-row asd-row--link" @click="$emit('open-advanced-query')">
        Custom Filter...
      </button>
    </div>

    <div class="asd-col">
      <span class="asd-col__title">Group By</span>
      <button
        v-for="g in resolvedStaticGroupFields"
        :key="g.id"
        type="button"
        class="asd-row"
        :class="{ 'asd-row--disabled': g.disabled }"
        :disabled="g.disabled"
        :title="g.disabled ? 'Coming soon' : ''"
        @click="toggleGroup(g)"
      >
        <font-awesome-icon
          icon="check"
          class="asd-row__check"
          :class="{ 'asd-row__check--hidden': !isGroupActive(g.id) }"
        />
        <span
          >{{ g.label
          }}<span v-if="g.disabled" class="asd-row__soon"> (will be done soon)</span></span
        >
      </button>

      <div v-if="isGroupActive('date')" class="asd-grain-row">
        <button
          v-for="grain in dateGrains"
          :key="grain"
          type="button"
          class="asd-grain"
          :class="{ 'asd-grain--active': dateGrain === grain }"
          @click="setDateGrain(grain)"
        >
          {{ grain }}
        </button>
      </div>

      <div class="asd-divider"></div>
      <button
        type="button"
        class="asd-row asd-row--link"
        @click="isCustomGroupOpen = !isCustomGroupOpen"
      >
        Custom Group
        <font-awesome-icon icon="chevron-down" class="asd-row__chevron" />
      </button>
      <div v-if="isCustomGroupOpen" class="asd-custom-group">
        <div v-if="customGroupLoading" class="asd-state text-muted">Loading…</div>
        <div v-else-if="!customGroupFields.length" class="asd-state text-muted">
          No other groupable fields
        </div>
        <button
          v-for="f in customGroupFields"
          :key="f.id"
          type="button"
          class="asd-row"
          @click="toggleGroup(f)"
        >
          <font-awesome-icon
            icon="check"
            class="asd-row__check"
            :class="{ 'asd-row__check--hidden': !isGroupActive(f.id) }"
          />
          <span>{{ f.label }}</span>
        </button>
      </div>
    </div>

    <div class="asd-col">
      <span class="asd-col__title">Favorites</span>
      <button
        type="button"
        class="asd-row asd-row--link asd-row--disabled"
        disabled
        title="Coming soon"
      >
        Save current search
        <font-awesome-icon icon="chevron-down" class="asd-row__chevron" />
      </button>
    </div>
  </div>
</template>

<script>
import { QUICK_FILTERS, STATIC_GROUP_FIELDS } from "@/quickSearchOptions.js";

export default {
  name: "AdvancedSearchDropdown",
  props: {
    activeFilters: { type: Array, required: true },
    groupByFields: { type: Array, required: true },
    customGroupFields: { type: Array, default: () => [] },
    customGroupLoading: { type: Boolean, default: false },
    dataType: { type: String, default: "" },
  },
  emits: ["update:active-filters", "update:group-by-fields", "open-advanced-query"],
  data() {
    return {
      isCustomGroupOpen: false,
      quickFilters: QUICK_FILTERS,
      staticGroupFields: STATIC_GROUP_FIELDS,
      dateGrains: ["day", "week", "month", "year"],
    };
  },
  computed: {
    resolvedStaticGroupFields() {
      return this.staticGroupFields.map((f) =>
        f.id === "type" ? { ...f, disabled: this.dataType !== "samples" } : f,
      );
    },
    dateGrain() {
      const entry = this.groupByFields.find((g) => g.id === "date");
      return entry?.grain || "month";
    },
  },
  methods: {
    toggleFilter(id) {
      const next = this.activeFilters.includes(id)
        ? this.activeFilters.filter((f) => f !== id)
        : [...this.activeFilters, id];
      this.$emit("update:active-filters", next);
    },
    isGroupActive(id) {
      return this.groupByFields.some((g) => g.id === id);
    },
    toggleGroup(field) {
      if (field.disabled) return;
      const exists = this.isGroupActive(field.id);
      const next = exists
        ? this.groupByFields.filter((g) => g.id !== field.id)
        : [...this.groupByFields, { id: field.id, label: field.label, grain: "month" }];
      this.$emit("update:group-by-fields", next);
    },
    setDateGrain(grain) {
      const next = this.groupByFields.map((g) => (g.id === "date" ? { ...g, grain } : g));
      this.$emit("update:group-by-fields", next);
    },
  },
};
</script>

<style scoped>
.asd-panel {
  display: flex;
  gap: 0;
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  padding: 10px 0;
  min-width: 560px;
}
.asd-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0 6px;
  border-right: 1px solid #f0f0f0;
}
.asd-col:last-child {
  border-right: none;
}
.asd-col__title {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #9ca3af;
  padding: 4px 10px 6px;
}
.asd-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  padding: 6px 10px;
  font-size: 0.85rem;
  color: #374151;
  border-radius: 6px;
  cursor: pointer;
}
.asd-row:hover:not(:disabled) {
  background: #f5f3ff;
}
.asd-row--disabled {
  color: #adb5bd;
  cursor: not-allowed;
}
.asd-row--link {
  color: #6366f1;
  justify-content: space-between;
}
.asd-row__check {
  font-size: 0.7rem;
  color: #6366f1;
  width: 12px;
  flex-shrink: 0;
}
.asd-row__check--hidden {
  visibility: hidden;
}
.asd-row__chevron {
  font-size: 0.6rem;
  opacity: 0.6;
}
.asd-row__soon {
  color: #adb5bd;
  font-size: 0.75rem;
}
.asd-divider {
  height: 1px;
  background: #f0f0f0;
  margin: 6px 4px;
}
.asd-state {
  padding: 4px 10px;
  font-size: 0.8rem;
}
.asd-grain-row {
  display: flex;
  gap: 4px;
  padding: 2px 10px 6px;
}
.asd-grain {
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 12px;
  font-size: 0.72rem;
  padding: 2px 10px;
  cursor: pointer;
  color: #6b7280;
  text-transform: capitalize;
}
.asd-grain--active {
  background: #6366f1;
  border-color: #6366f1;
  color: #fff;
}
.asd-custom-group {
  padding-left: 4px;
  max-height: 160px;
  overflow-y: auto;
}
</style>
