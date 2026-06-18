<template>
  <div class="dt-range">
    <div class="dt-range__row">
      <span class="dt-range__label">From</span>
      <input
        :value="modelValue && modelValue[0]"
        type="datetime-local"
        class="qeditor-input"
        @input="onStart($event.target.value)"
      />
    </div>
    <div class="dt-range__row">
      <span class="dt-range__label">To</span>
      <input
        :value="modelValue && modelValue[1]"
        type="datetime-local"
        class="qeditor-input"
        @input="onEnd($event.target.value)"
      />
    </div>
  </div>
</template>

<script>
export default {
  name: "DatetimeRangeEditor",
  props: {
    modelValue: { type: Array, default: () => ["", ""] },
  },
  emits: ["update:modelValue"],
  methods: {
    onStart(val) {
      this.$emit("update:modelValue", [val, (this.modelValue && this.modelValue[1]) || ""]);
    },
    onEnd(val) {
      this.$emit("update:modelValue", [(this.modelValue && this.modelValue[0]) || "", val]);
    },
  },
};
</script>

<style scoped>
.dt-range {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.dt-range__row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.dt-range__label {
  font-size: 0.72rem;
  color: #868e96;
  width: 28px;
  flex-shrink: 0;
}
.qeditor-input {
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 3px 6px;
  font-size: 0.875rem;
  color: #374151;
  outline: none;
  background: transparent;
  width: 100%;
}
.qeditor-input:focus {
  border-color: #6366f1;
}
</style>
