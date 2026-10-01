<template>
  <div class="enum-editor">
    <div v-if="isMulti" class="enum-chips">
      <span v-for="v in selectedArray" :key="v" class="enum-chip">
        {{ v }}<button class="enum-chip__remove" @click="removeChip(v)">×</button>
      </span>
      <select
        v-if="remainingOptions.length"
        class="enum-add-select"
        @change="addChip($event.target.value)"
      >
        <option value="">+ Add…</option>
        <option v-for="opt in remainingOptions" :key="opt" :value="opt">{{ opt }}</option>
      </select>
    </div>

    <div v-else class="enum-chips">
      <span v-if="modelValue" class="enum-chip">
        {{ modelValue
        }}<button class="enum-chip__remove" @click="$emit('update:modelValue', '')">×</button>
      </span>
      <select
        v-else
        class="enum-add-select enum-add-select--full"
        @change="$emit('update:modelValue', $event.target.value)"
      >
        <option value="" disabled selected>Select…</option>
        <option v-for="opt in options" :key="opt" :value="opt">{{ opt }}</option>
      </select>
    </div>
  </div>
</template>

<script>
export default {
  name: "EnumEditor",
  props: {
    modelValue: { type: [String, Array], default: null },
    valueSchema: { type: Object, default: () => ({}) },
  },
  emits: ["update:modelValue"],
  computed: {
    isMulti() {
      return this.valueSchema && this.valueSchema.type === "array";
    },
    options() {
      if (this.isMulti) {
        return this.valueSchema?.items?.enum || [];
      }
      return this.valueSchema?.enum || [];
    },
    selectedArray() {
      if (!this.modelValue) return [];
      return Array.isArray(this.modelValue) ? this.modelValue : [this.modelValue];
    },
    remainingOptions() {
      return this.options.filter((o) => !this.selectedArray.includes(o));
    },
  },
  methods: {
    addChip(val) {
      if (!val) return;
      this.$emit("update:modelValue", [...this.selectedArray, val]);
    },
    removeChip(val) {
      const next = this.selectedArray.filter((v) => v !== val);
      this.$emit("update:modelValue", next.length ? next : null);
    },
  },
};
</script>

<style scoped>
.enum-editor {
  width: 100%;
}

.enum-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  min-height: 28px;
}

.enum-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px 2px 10px;
  background: #ede9fe;
  color: #5b21b6;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
}
.enum-chip__remove {
  background: none;
  border: none;
  color: #7c3aed;
  cursor: pointer;
  padding: 0;
  font-size: 0.95rem;
  line-height: 1;
  opacity: 0.7;
}
.enum-chip__remove:hover {
  opacity: 1;
}

.enum-add-select {
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.8rem;
  color: #9ca3af;
  cursor: pointer;
  padding: 0;
}
.enum-add-select--full {
  font-size: 0.875rem;
  color: #374151;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%239ca3af'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0 center;
  padding-right: 14px;
}
</style>
