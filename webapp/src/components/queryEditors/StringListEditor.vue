<template>
  <input
    :value="displayValue"
    type="text"
    class="form-control form-control-sm"
    placeholder="val1, val2, ..."
    @input="onInput($event.target.value)"
  />
</template>

<script>
export default {
  name: "StringListEditor",
  props: {
    modelValue: { type: Array, default: () => [] },
  },
  emits: ["update:modelValue"],
  computed: {
    displayValue() {
      return Array.isArray(this.modelValue) ? this.modelValue.join(", ") : "";
    },
  },
  methods: {
    onInput(raw) {
      const items = raw
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      this.$emit("update:modelValue", items);
    },
  },
};
</script>
