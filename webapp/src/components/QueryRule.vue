<template>
  <div class="qr">
    <div class="qr__field">
      <span class="qr__field-icon">{{ fieldIcon }}</span>
      <!-- TODO: Render structured subfields hierarchically; flat dot-path fields work for now. -->
      <select :value="node.field" class="qr__select" @change="onFieldChange($event.target.value)">
        <option value="" disabled>Field…</option>
        <optgroup v-for="group in groupedFields" :key="group.label" :label="group.label">
          <option v-for="f in group.fields" :key="f.id" :value="f.id">{{ f.label }}</option>
        </optgroup>
      </select>
    </div>

    <div class="qr__operator">
      <select
        :value="node.operator"
        class="qr__select"
        :disabled="!node.field"
        @change="onOperatorChange($event.target.value)"
      >
        <option value="" disabled>Operator…</option>
        <option v-for="op in availableOperators" :key="op.id" :value="op.id">{{ op.label }}</option>
      </select>
    </div>

    <div class="qr__value">
      <component
        :is="editorComponent"
        v-if="currentOperator && currentOperator.value_required"
        :model-value="node.value"
        :value-schema="currentOperator.value_schema"
        :options-source="currentOperator.options_source"
        @update:model-value="onValueChange"
      />
      <span v-else-if="currentOperator && !currentOperator.value_required" class="qr__no-value">
        no value needed
      </span>
    </div>

    <button class="qr__delete" title="Remove" @click="$emit('remove')">
      <font-awesome-icon icon="trash" />
    </button>
  </div>
</template>

<script>
import TextEditor from "@/components/queryEditors/TextEditor.vue";
import StringListEditor from "@/components/queryEditors/StringListEditor.vue";
import NumberEditor from "@/components/queryEditors/NumberEditor.vue";
import DatetimeEditor from "@/components/queryEditors/DatetimeEditor.vue";
import DatetimeRangeEditor from "@/components/queryEditors/DatetimeRangeEditor.vue";
import EnumEditor from "@/components/queryEditors/EnumEditor.vue";
import ChemicalFormulaEditor from "@/components/queryEditors/ChemicalFormulaEditor.vue";
import ConstituentSelectorEditor from "@/components/queryEditors/ConstituentSelectorEditor.vue";
import FallbackEditor from "@/components/queryEditors/FallbackEditor.vue";

const editorMap = {
  text: "TextEditor",
  "string-list": "StringListEditor",
  number: "NumberEditor",
  datetime: "DatetimeEditor",
  "datetime-range": "DatetimeRangeEditor",
  enum: "EnumEditor",
  "chemical-formula": "ChemicalFormulaEditor",
  "constituent-selector": "ConstituentSelectorEditor",
};

const groupIcons = {
  Basic: "Aa",
  Chemistry: "⚗",
  Cell: "⊙",
  Synthesis: "∑",
  Provenance: "◈",
  Other: "◇",
};

export default {
  name: "QueryRule",
  components: {
    TextEditor,
    StringListEditor,
    NumberEditor,
    DatetimeEditor,
    DatetimeRangeEditor,
    EnumEditor,
    ChemicalFormulaEditor,
    ConstituentSelectorEditor,
    FallbackEditor,
  },
  props: {
    node: { type: Object, required: true },
    fields: { type: Array, required: true },
  },
  emits: ["update:node", "remove"],
  computed: {
    groupedFields() {
      const groups = {};
      this.fields.forEach((f) => {
        const g = f.group || "Other";
        if (!groups[g]) groups[g] = { label: g, fields: [] };
        groups[g].fields.push(f);
      });
      return Object.values(groups);
    },
    currentField() {
      return this.fields.find((f) => f.id === this.node.field) || null;
    },
    availableOperators() {
      return this.currentField ? this.currentField.operators : [];
    },
    currentOperator() {
      if (!this.currentField) return null;
      return this.currentField.operators.find((op) => op.id === this.node.operator) || null;
    },
    editorComponent() {
      if (!this.currentOperator) return null;
      return editorMap[this.currentOperator.editor] || "FallbackEditor";
    },
    fieldIcon() {
      if (!this.currentField) return "◇";
      return groupIcons[this.currentField.group] || "◇";
    },
  },
  methods: {
    onFieldChange(fieldId) {
      const field = this.fields.find((f) => f.id === fieldId);
      const firstOp = field?.operators[0]?.id || "";
      this.$emit("update:node", {
        ...this.node,
        field: fieldId,
        operator: firstOp,
        value: undefined,
      });
    },
    onOperatorChange(opId) {
      this.$emit("update:node", { ...this.node, operator: opId, value: undefined });
    },
    onValueChange(value) {
      this.$emit("update:node", { ...this.node, value });
    },
  },
};
</script>

<style scoped>
.qr {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 36px;
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  background: #fff;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  transition: border-color 0.12s;
}
.qr:hover {
  border-color: #d1d5db;
}

.qr__field {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.qr__field-icon {
  font-size: 0.8rem;
  color: #9ca3af;
  flex-shrink: 0;
  width: 18px;
  text-align: center;
}
.qr__operator,
.qr__value {
  min-width: 0;
}

.qr__select {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.875rem;
  color: #374151;
  cursor: pointer;
  padding: 0;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%239ca3af'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0 center;
  padding-right: 14px;
}
.qr__select:disabled {
  color: #d1d5db;
  cursor: not-allowed;
}

.qr__no-value {
  font-size: 0.78rem;
  color: #d1d5db;
  font-style: italic;
}

.qr__delete {
  background: none;
  border: none;
  color: #d1d5db;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  font-size: 0.8rem;
  transition: color 0.12s;
  justify-self: center;
}
.qr__delete:hover {
  color: #ef4444;
}
</style>
