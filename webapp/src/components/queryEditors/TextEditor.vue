<template>
  <input
    :value="modelValue"
    type="text"
    class="qeditor-input"
    placeholder="Enter value…"
    @input="$emit('update:modelValue', $event.target.value)"
  />
</template>

<script>
export default {
  name: "TextEditor",
  props: { modelValue: { type: String, default: "" } },
  emits: ["update:modelValue"],
};
</script>

<style scoped>
.qeditor-input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.875rem;
  color: #374151;
  padding: 0;
}
.qeditor-input::placeholder {
  color: #d1d5db;
}
</style>
