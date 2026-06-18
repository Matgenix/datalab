<template>
  <div ref="root" class="adv-search">
    <button
      class="adv-trigger"
      :class="{ 'adv-trigger--active': appliedSummary }"
      @click="isOpen = true"
    >
      <font-awesome-icon icon="filter" class="adv-trigger__icon" />
      <span class="adv-trigger__label" :title="appliedSummary || ''">
        {{ appliedSummary || "Advanced Search" }}
      </span>
      <span
        v-if="appliedSummary"
        class="adv-trigger__clear"
        title="Clear filters"
        @click.stop="clearFilters"
        >×</span
      >
      <font-awesome-icon v-else icon="chevron-down" class="adv-trigger__chevron" />
    </button>

    <Teleport to="body">
      <Transition name="adv-modal">
        <div v-if="isOpen" class="adv-overlay" @click.self="isOpen = false">
          <div class="adv-modal" role="dialog">
            <div class="adv-modal__header">
              <span class="adv-modal__title">Advanced Search</span>
              <button class="adv-modal__close" aria-label="Close" @click="isOpen = false">
                <font-awesome-icon icon="times" />
              </button>
            </div>

            <div class="adv-modal__body">
              <div v-if="typesLoading" class="adv-state text-muted">Loading…</div>
              <div v-else-if="typesError" class="adv-state text-danger">{{ typesError }}</div>

              <div v-else class="adv-type-row">
                <span class="adv-section-label">Item type</span>
                <div class="d-flex" style="gap: 20px">
                  <div v-for="t in queryableTypes" :key="t.id" class="form-check mb-0">
                    <input
                      :id="`adv-qt-${t.id}`"
                      v-model="selectedType"
                      type="radio"
                      :value="t.id"
                      class="form-check-input"
                      @change="onTypeChange(t.id)"
                    />
                    <label :for="`adv-qt-${t.id}`" class="form-check-label">{{ t.label }}</label>
                  </div>
                </div>
              </div>

              <div v-if="pendingTypeChange" class="alert alert-warning py-2 px-3 small mb-0 mt-3">
                {{ stalRulesCount }} condition(s) will be cleared when switching type.
                <div class="mt-1 d-flex gap-2">
                  <button class="btn btn-sm btn-warning" @click="confirmTypeChange">Confirm</button>
                  <button class="btn btn-sm btn-outline-secondary" @click="cancelTypeChange">
                    Cancel
                  </button>
                </div>
              </div>

              <div v-if="schemaLoading" class="adv-state text-muted mt-3">Loading fields…</div>
              <div v-else-if="schemaError" class="adv-state text-danger mt-3">
                {{ schemaError }}
              </div>

              <template v-else-if="schema">
                <div class="adv-sort-row">
                  <span class="adv-section-label">Sort by</span>
                  <select v-model="sortField" class="adv-sort-select">
                    <option value="">Default (date, newest first)</option>
                    <option v-for="f in sortableFields" :key="f.id" :value="f.id">
                      {{ f.label }}
                    </option>
                  </select>
                  <button
                    v-if="sortField"
                    class="adv-sort-dir"
                    :title="sortDirection === 'desc' ? 'Descending' : 'Ascending'"
                    @click="sortDirection = sortDirection === 'desc' ? 'asc' : 'desc'"
                  >
                    {{ sortDirection === "desc" ? "↓ Desc" : "↑ Asc" }}
                  </button>
                </div>

                <div class="adv-rules-area">
                  <div v-if="rootGroup.children.length" class="adv-rules-header">
                    <span>Field</span>
                    <span>Operator</span>
                    <span>Value</span>
                    <span></span>
                  </div>

                  <QueryGroup
                    :node="rootGroup"
                    :fields="schema.fields"
                    :max-depth="schema.capabilities.max_depth"
                    :current-depth="0"
                    @update:node="rootGroup = $event"
                  />
                </div>
              </template>
            </div>

            <div class="adv-modal__footer">
              <span v-if="queryError" class="adv-footer-error">{{ queryError }}</span>
              <span v-else-if="previewCount !== null" class="adv-preview-count">
                <font-awesome-icon v-if="previewLoading" icon="sync" spin class="me-1" />
                <template v-else>Found: {{ previewCount }}</template>
              </span>
              <span v-else-if="previewLoading" class="adv-preview-count">
                <font-awesome-icon icon="sync" spin class="me-1" /> Counting…
              </span>
              <div class="adv-footer-actions">
                <button class="btn-ghost" @click="isOpen = false">Cancel</button>
                <button class="btn-primary" :disabled="queryLoading" @click="submitQuery">
                  <font-awesome-icon v-if="queryLoading" icon="sync" spin class="me-1" />
                  <span v-else>Search</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script>
import { fetchItemTypes, fetchQuerySchema, runItemQuery } from "@/server_fetch_utils.js";
import QueryGroup from "@/components/QueryGroup.vue";

export default {
  name: "AdvancedQueryBuilder",
  components: { QueryGroup },
  props: {
    listView: { type: String, default: "samples" },
  },
  emits: ["query-results"],
  data() {
    return {
      isOpen: false,
      itemTypes: [],
      typesLoading: false,
      typesError: null,
      selectedType: null,
      pendingTypeChange: null,
      stalRulesCount: 0,
      schema: null,
      schemaLoading: false,
      schemaError: null,
      rootGroup: this.emptyGroup(),
      queryLoading: false,
      queryError: null,
      appliedSummary: null,
      sortField: "",
      sortDirection: "desc",
      previewCount: null,
      previewLoading: false,
      previewTimer: null,
    };
  },
  computed: {
    queryableTypes() {
      return this.itemTypes.filter((t) => t.queryable);
    },
    sortableFields() {
      return (this.schema?.fields || []).filter((f) => f.sortable);
    },
  },
  watch: {
    rootGroup: {
      deep: true,
      handler() {
        this.schedulePreview();
      },
    },
    selectedType() {
      this.schedulePreview();
    },
  },
  async mounted() {
    this.typesLoading = true;
    try {
      const result = await fetchItemTypes(this.listView);
      this.itemTypes = result.item_types || [];
      if (this.itemTypes.length) {
        this.selectedType = this.itemTypes[0].id;
        await this.loadSchema(this.selectedType);
      }
    } catch (e) {
      this.typesError = e.message;
    } finally {
      this.typesLoading = false;
    }
  },
  beforeUnmount() {
    clearTimeout(this.previewTimer);
  },
  methods: {
    emptyGroup() {
      return { kind: "group", combinator: "and", children: [] };
    },

    async loadSchema(typeId) {
      this.schemaLoading = true;
      this.schemaError = null;
      try {
        this.schema = await fetchQuerySchema(this.listView, [typeId]);
      } catch (e) {
        this.schemaError = e.message;
      } finally {
        this.schemaLoading = false;
      }
    },

    countStaleRules(node, validFieldIds) {
      if (node.kind === "rule") return validFieldIds.includes(node.field) ? 0 : 1;
      return (node.children || []).reduce(
        (sum, child) => sum + this.countStaleRules(child, validFieldIds),
        0,
      );
    },

    async onTypeChange(newTypeId) {
      if (!this.schema || !this.rootGroup.children.length) {
        this.selectedType = newTypeId;
        await this.loadSchema(newTypeId);
        return;
      }
      const newSchema = await fetchQuerySchema(this.listView, [newTypeId]).catch(() => null);
      const newFieldIds = newSchema ? newSchema.fields.map((f) => f.id) : [];
      const stale = this.countStaleRules(this.rootGroup, newFieldIds);
      if (stale === 0) {
        this.selectedType = newTypeId;
        this.schema = newSchema;
        return;
      }
      this.stalRulesCount = stale;
      this.pendingTypeChange = { typeId: newTypeId, schema: newSchema };
    },

    confirmTypeChange() {
      const { typeId, schema } = this.pendingTypeChange;
      this.selectedType = typeId;
      this.schema = schema;
      this.rootGroup = this.emptyGroup();
      this.pendingTypeChange = null;
    },

    cancelTypeChange() {
      this.pendingTypeChange = null;
    },

    stripInternalProps(node) {
      if (node.kind === "rule") {
        const { field, operator, value } = node;
        return value !== undefined
          ? { kind: "rule", field, operator, value }
          : { kind: "rule", field, operator };
      }
      return {
        kind: "group",
        combinator: node.combinator,
        children: (node.children || []).map((c) => this.stripInternalProps(c)),
      };
    },

    buildSummary(node) {
      if (!this.schema) return null;
      if (node.kind === "rule") {
        if (!node.field || !node.operator) return null;
        const field = this.schema.fields.find((f) => f.id === node.field);
        const op = field?.operators.find((o) => o.id === node.operator);
        const fieldLabel = field?.label || node.field;
        const opLabel = op?.label || node.operator;
        if (!op?.value_required) return `${fieldLabel} ${opLabel}`;
        const val = Array.isArray(node.value) ? node.value.filter(Boolean).join(", ") : node.value;
        return val ? `${fieldLabel} ${opLabel} "${val}"` : `${fieldLabel} ${opLabel}`;
      }
      if (node.kind === "group") {
        const parts = (node.children || []).map((c) => this.buildSummary(c)).filter(Boolean);
        if (!parts.length) return null;
        return parts.join(node.combinator === "or" ? " OR " : " AND ");
      }
      return null;
    },

    validateRules(node) {
      if (node.kind === "rule") {
        if (!node.field) return "Select a field for all rules.";
        if (!node.operator) return "Select an operator for all rules.";
        const field = this.schema?.fields.find((f) => f.id === node.field);
        const op = field?.operators.find((o) => o.id === node.operator);
        if (op?.value_required) {
          const v = node.value;
          const isEmpty =
            v === undefined ||
            v === null ||
            v === "" ||
            (Array.isArray(v) && v.filter(Boolean).length === 0);
          if (isEmpty) return `"${field?.label || node.field}": value is required.`;
          if (op.editor === "datetime-range") {
            const [from, to] = Array.isArray(v) ? v : ["", ""];
            if (!from) return `"${field?.label || node.field}": start date is required.`;
            if (!to) return `"${field?.label || node.field}": end date is required.`;
          }
        }
        return null;
      }
      if (node.kind === "group") {
        for (const child of node.children || []) {
          const err = this.validateRules(child);
          if (err) return err;
        }
      }
      return null;
    },

    buildRequest(pageOptions = {}) {
      const req = {
        list_view: this.listView,
        item_types: [this.selectedType],
        where: this.stripInternalProps(this.rootGroup),
      };
      if (this.sortField) {
        req.sort = [{ field: this.sortField, direction: this.sortDirection }];
      }
      if (Object.keys(pageOptions).length) {
        req.page = pageOptions;
      }
      return req;
    },

    schedulePreview() {
      clearTimeout(this.previewTimer);
      if (!this.rootGroup.children.length) {
        this.previewCount = null;
        return;
      }
      this.previewLoading = true;
      this.previewTimer = setTimeout(() => this.fetchPreview(), 400);
    },

    async fetchPreview() {
      if (!this.selectedType || !this.schema) return;
      if (this.validateRules(this.rootGroup)) {
        this.previewLoading = false;
        this.previewCount = null;
        return;
      }
      try {
        const result = await runItemQuery(this.buildRequest({ limit: 200 }));
        const count = result.items?.length ?? 0;
        this.previewCount = result.page?.has_more
          ? `${count}+ items`
          : `${count} item${count !== 1 ? "s" : ""}`;
      } catch {
        this.previewCount = null;
      } finally {
        this.previewLoading = false;
      }
    },

    async submitQuery() {
      this.queryError = null;
      const validationError = this.validateRules(this.rootGroup);
      if (validationError) {
        this.queryError = validationError;
        return;
      }
      this.queryLoading = true;
      try {
        const allItems = [];
        let cursor = null;
        const SAFETY_LIMIT = 2000;

        do {
          const pageOpts = { limit: 200 };
          if (cursor) pageOpts.cursor = cursor;
          const result = await runItemQuery(this.buildRequest(pageOpts));
          allItems.push(...(result.items || []));
          cursor = result.page?.has_more ? result.page.next_cursor : null;
        } while (cursor && allItems.length < SAFETY_LIMIT);

        this.appliedSummary = this.buildSummary(this.rootGroup);
        this.$emit("query-results", allItems);
        this.isOpen = false;
      } catch (e) {
        if (e instanceof TypeError && e.message === "Failed to fetch") {
          this.queryError = "Cannot reach the server. Check your connection.";
        } else {
          this.queryError = e.message || "Query failed. Please try again.";
        }
      } finally {
        this.queryLoading = false;
      }
    },

    clearFilters() {
      this.rootGroup = this.emptyGroup();
      this.appliedSummary = null;
      this.sortField = "";
      this.sortDirection = "desc";
      this.previewCount = null;
      this.queryError = null;
      this.$emit("query-results", null);
    },
  },
};
</script>

<style scoped>
.adv-search {
  display: inline-block;
}

.adv-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 20px;
  font-size: 0.85rem;
  color: #495057;
  cursor: pointer;
  max-width: 320px;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.adv-trigger:hover {
  border-color: #adb5bd;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}
.adv-trigger--active {
  border-color: #6366f1;
  color: #6366f1;
  background: #f5f3ff;
}
.adv-trigger__icon {
  flex-shrink: 0;
  opacity: 0.6;
}
.adv-trigger__label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}
.adv-trigger__chevron {
  flex-shrink: 0;
  font-size: 0.65rem;
  opacity: 0.4;
}
.adv-trigger__clear {
  flex-shrink: 0;
  font-size: 1rem;
  line-height: 1;
  color: #6366f1;
  opacity: 0.7;
  cursor: pointer;
  padding: 0 2px;
  border-radius: 50%;
}
.adv-trigger__clear:hover {
  opacity: 1;
  background: rgba(99, 102, 241, 0.1);
}

.adv-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.adv-modal {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.18);
  width: 700px;
  max-width: 95vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.adv-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px 14px;
  border-bottom: 1px solid #f0f0f0;
}
.adv-modal__title {
  font-size: 1rem;
  font-weight: 600;
  color: #1a1a2e;
}
.adv-modal__close {
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  font-size: 1rem;
  line-height: 1;
  transition:
    background 0.12s,
    color 0.12s;
}
.adv-modal__close:hover {
  background: #f3f4f6;
  color: #374151;
}

.adv-modal__body {
  padding: 20px 24px 8px;
  overflow-y: auto;
  flex: 1;
}

.adv-modal__footer {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 24px;
  border-top: 1px solid #f0f0f0;
}
.adv-footer-error {
  flex: 1;
  font-size: 0.8rem;
  color: #ef4444;
}
.adv-preview-count {
  flex: 1;
  font-size: 0.8rem;
  color: #6b7280;
}
.adv-footer-actions {
  display: flex;
  gap: 10px;
  margin-left: auto;
}

.adv-type-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 14px;
  background: #f9fafb;
  border: 1px solid #e9ecef;
  border-radius: 8px;
}
.adv-sort-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  background: #f9fafb;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  margin-top: 10px;
}
.adv-sort-select {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 0.875rem;
  color: #374151;
  outline: none;
  cursor: pointer;
}
.adv-sort-dir {
  background: none;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 0.78rem;
  color: #6366f1;
  cursor: pointer;
  padding: 2px 10px;
  white-space: nowrap;
  transition: background 0.12s;
}
.adv-sort-dir:hover {
  background: #f5f3ff;
}

.adv-section-label {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #9ca3af;
  white-space: nowrap;
}
.adv-state {
  padding: 6px 0;
  font-size: 0.875rem;
}

.adv-rules-area {
  margin-top: 16px;
}
.adv-rules-header {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 32px;
  gap: 10px;
  padding: 0 0 6px 0;
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #9ca3af;
}

.btn-ghost {
  background: none;
  border: 1px solid #e5e7eb;
  color: #6b7280;
  border-radius: 8px;
  padding: 6px 16px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 0.12s;
}
.btn-ghost:hover {
  background: #f9fafb;
}

.btn-primary {
  background: #6366f1;
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 0.875rem;
  font-weight: 500;
  padding: 6px 24px;
  cursor: pointer;
  transition: background 0.12s;
}
.btn-primary:hover {
  background: #4f46e5;
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.adv-modal-enter-active,
.adv-modal-leave-active {
  transition: opacity 0.2s ease;
}
.adv-modal-enter-active .adv-modal,
.adv-modal-leave-active .adv-modal {
  transition:
    transform 0.2s ease,
    opacity 0.2s ease;
}
.adv-modal-enter-from,
.adv-modal-leave-to {
  opacity: 0;
}
.adv-modal-enter-from .adv-modal,
.adv-modal-leave-to .adv-modal {
  transform: scale(0.95);
  opacity: 0;
}
</style>
