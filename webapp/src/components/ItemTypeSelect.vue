<template>
  <Select
    :model-value="modelValue"
    :options="types"
    :input-id="inputId"
    :disabled="disabled"
    :required="required"
    class="item-type-select w-100"
    append-to="self"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <template #value="slotProps">
      <component :is="badgeComponent" v-if="slotProps.value" :type="slotProps.value" />
      <span v-else>{{ slotProps.placeholder }}</span>
    </template>
    <template #option="slotProps">
      <component :is="badgeComponent" :type="slotProps.option" />
    </template>
  </Select>
</template>

<script>
import Select from "primevue/select";

import ItemTypeBadge from "@/components/ItemTypeBadge.vue";

export default {
  name: "ItemTypeSelect",
  components: { Select },
  props: {
    modelValue: {
      type: String,
      default: "",
    },
    types: {
      type: Array,
      required: true,
    },
    inputId: {
      type: String,
      default: null,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    required: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["update:modelValue"],
  computed: {
    badgeComponent() {
      return ItemTypeBadge;
    },
  },
};
</script>

<style scoped>
.item-type-select {
  min-height: calc(1.5em + 0.75rem + 2px);
}
</style>
