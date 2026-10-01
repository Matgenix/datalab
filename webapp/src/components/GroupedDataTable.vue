<template>
  <div class="grouped-table">
    <div v-if="showHeader" class="grouped-header-row">
      <span class="grouped-header-row__checkbox"></span>
      <span v-for="col in effectiveColumns" :key="col.field" class="grouped-header-row__cell">{{
        col.header
      }}</span>
    </div>

    <template v-if="!groupFields.length">
      <div
        v-for="row in items"
        :key="rowKey(row)"
        class="grouped-leaf-row"
        @click="onRowClick(row)"
      >
        <input
          type="checkbox"
          class="grouped-leaf-row__checkbox"
          :checked="isSelected(row)"
          @click.stop="toggleSelected(row)"
        />
        <span v-for="col in effectiveColumns" :key="col.field" class="grouped-leaf-row__cell">{{
          cellValue(row, col)
        }}</span>
      </div>
      <div v-if="!items.length" class="grouped-empty text-muted">No items</div>
    </template>

    <template v-else>
      <div v-for="bucket in buckets" :key="bucket.key" class="grouped-bucket">
        <button type="button" class="grouped-bucket__header" @click="toggle(bucket.key)">
          <font-awesome-icon
            icon="chevron-right"
            class="grouped-bucket__chevron"
            :class="{ 'grouped-bucket__chevron--open': isExpanded(bucket.key) }"
          />
          <span class="grouped-bucket__label">{{ bucket.label }}</span>
          <span class="grouped-bucket__count">({{ bucket.items.length }})</span>
        </button>
        <GroupedDataTable
          v-if="isExpanded(bucket.key)"
          class="grouped-bucket__children"
          :items="bucket.items"
          :group-fields="groupFields.slice(1)"
          :items-selected="itemsSelected"
          :columns="columns"
          :show-header="false"
          @update:items-selected="$emit('update:items-selected', $event)"
          @row-click="$emit('row-click', $event)"
        />
      </div>
    </template>
  </div>
</template>

<script>
const FALLBACK_COLUMNS = [
  { field: "item_id", header: "ID" },
  { field: "name", header: "Name" },
  { field: "status", header: "Status" },
  { field: "date", header: "Date" },
];

export default {
  name: "GroupedDataTable",
  props: {
    items: { type: Array, required: true },
    groupFields: { type: Array, required: true },
    itemsSelected: { type: Array, required: true },
    columns: { type: Array, default: () => [] },
    showHeader: { type: Boolean, default: true },
  },
  emits: ["update:items-selected", "row-click"],
  data() {
    return {
      expanded: new Set(),
    };
  },
  computed: {
    effectiveColumns() {
      const withHeaders = this.columns.filter((c) => c.field && c.header);
      return withHeaders.length ? withHeaders : FALLBACK_COLUMNS;
    },
    buckets() {
      const field = this.groupFields[0];
      const map = new Map();
      for (const item of this.items) {
        for (const { key, label } of this.getGroupValues(item, field)) {
          if (!map.has(key)) {
            map.set(key, { key, label, items: [] });
          }
          map.get(key).items.push(item);
        }
      }
      return [...map.values()].sort((a, b) => a.label.localeCompare(b.label));
    },
  },
  methods: {
    rowKey(row) {
      return row.item_id || row.collection_id || row.immutable_id || row._id;
    },
    isSelected(row) {
      return this.itemsSelected.some((r) => this.rowKey(r) === this.rowKey(row));
    },
    toggleSelected(row) {
      const next = this.isSelected(row)
        ? this.itemsSelected.filter((r) => this.rowKey(r) !== this.rowKey(row))
        : [...this.itemsSelected, row];
      this.$emit("update:items-selected", next);
    },
    onRowClick(row) {
      this.$emit("row-click", row);
    },
    isExpanded(key) {
      return this.expanded.has(key);
    },
    toggle(key) {
      const next = new Set(this.expanded);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      this.expanded = next;
    },
    formatDate(value) {
      const d = new Date(value);
      return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString();
    },
    cellValue(row, col) {
      const value = row[col.field];
      if (value === undefined || value === null || value === "") return "";
      if (Array.isArray(value)) {
        if (value.length && typeof value[0] === "object") {
          return value
            .map((v) => v.display_name || v.collection_id || v.title)
            .filter(Boolean)
            .join(", ");
        }
        return String(value.length);
      }
      if (typeof value === "object") {
        return value.display_name || value.title || "";
      }
      if (["date", "date_opened", "last_modified"].includes(col.field)) {
        return this.formatDate(value);
      }
      return String(value);
    },
    getGroupValues(item, field) {
      if (field.id === "status") {
        const value = item.status;
        return [{ key: value || "__none__", label: value || "No status" }];
      }
      if (field.id === "creators") {
        const creators = item.creators || [];
        if (!creators.length) return [{ key: "__none__", label: "No creator" }];
        return creators.map((c) => ({
          key: c.display_name || "__none__",
          label: c.display_name || "No creator",
        }));
      }
      if (field.id === "date") {
        return [this.getDateBucket(item.date, field.grain || "month")];
      }
      const value = item[field.id];
      if (value === undefined || value === null || value === "") {
        return [{ key: "__none__", label: "No value" }];
      }
      return [{ key: String(value), label: String(value) }];
    },
    getDateBucket(value, grain) {
      const d = value ? new Date(value) : null;
      if (!d || Number.isNaN(d.getTime())) {
        return { key: "__none__", label: "No date" };
      }
      const y = d.getFullYear();
      const m = d.getMonth();
      if (grain === "day") {
        const key = d.toISOString().slice(0, 10);
        return { key, label: d.toLocaleDateString() };
      }
      if (grain === "week") {
        const firstDay = new Date(d);
        firstDay.setDate(d.getDate() - d.getDay());
        const key = firstDay.toISOString().slice(0, 10);
        return { key: `week-${key}`, label: `Week of ${firstDay.toLocaleDateString()}` };
      }
      if (grain === "year") {
        return { key: `${y}`, label: `${y}` };
      }
      const key = `${y}-${String(m + 1).padStart(2, "0")}`;
      const label = d.toLocaleDateString(undefined, { month: "long", year: "numeric" });
      return { key, label };
    },
  },
};
</script>

<style scoped>
.grouped-table {
  width: 100%;
}
.grouped-header-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 12px;
  border-bottom: 2px solid #e9ecef;
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #9ca3af;
}
.grouped-header-row__checkbox {
  width: 14px;
  flex-shrink: 0;
}
.grouped-header-row__cell {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.grouped-bucket__header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  text-align: left;
  background: #f9fafb;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 8px 12px;
  margin: 4px 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
}
.grouped-bucket__header:hover {
  background: #f3f4f6;
}
.grouped-bucket__chevron {
  font-size: 0.7rem;
  color: #6366f1;
  transition: transform 0.12s;
}
.grouped-bucket__chevron--open {
  transform: rotate(90deg);
}
.grouped-bucket__count {
  color: #9ca3af;
  font-weight: 400;
}
.grouped-bucket__children {
  padding-left: 22px;
}
.grouped-leaf-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 7px 12px;
  border-bottom: 1px solid #f3f4f6;
  cursor: pointer;
  font-size: 0.85rem;
  color: #374151;
}
.grouped-leaf-row:hover {
  background: #f9fafb;
}
.grouped-leaf-row__cell {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.grouped-empty {
  padding: 10px 12px;
  font-size: 0.85rem;
}
</style>
