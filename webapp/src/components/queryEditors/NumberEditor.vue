<template>
  <input
    :value="modelValue"
    type="number"
    class="qeditor-input"
    placeholder="Enter number…"
    @input="$emit('update:modelValue', Number($event.target.value))"
  />
</template>

<script>
export default {
  name: "NumberEditor",
  props: { modelValue: { type: Number, default: null } },
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
