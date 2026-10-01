<template>
  <div class="position-relative">
    <input
      v-model="query"
      type="text"
      class="form-control form-control-sm"
      placeholder="Search..."
      autocomplete="off"
      @input="onInput"
      @blur="onBlur"
    />
    <ul v-if="options.length && showDropdown" class="constituent-dropdown list-unstyled mb-0">
      <li
        v-for="opt in options"
        :key="opt.id"
        class="constituent-option"
        @mousedown.prevent="selectOption(opt)"
      >
        {{ opt.label }}
      </li>
    </ul>
  </div>
</template>

<script>
import { fetchQueryOptions } from "@/server_fetch_utils.js";
import { debounceTime } from "@/resources.js";

export default {
  name: "ConstituentSelectorEditor",
  props: {
    modelValue: { type: String, default: "" },
    optionsSource: { type: String, default: "datalab:item-reference" },
  },
  emits: ["update:modelValue"],
  data() {
    return {
      query: this.modelValue || "",
      options: [],
      showDropdown: false,
      debounceTimer: null,
    };
  },
  methods: {
    onInput() {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(async () => {
        if (!this.query) {
          this.options = [];
          return;
        }
        try {
          const result = await fetchQueryOptions(this.optionsSource, this.query);
          this.options = result.options || [];
          this.showDropdown = true;
        } catch {
          this.options = [];
        }
      }, debounceTime);
    },
    selectOption(opt) {
      this.query = opt.label;
      this.showDropdown = false;
      this.$emit("update:modelValue", opt.value);
    },
    onBlur() {
      setTimeout(() => {
        this.showDropdown = false;
      }, 150);
    },
  },
};
</script>

<style scoped>
.constituent-dropdown {
  position: absolute;
  z-index: 1000;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  width: 100%;
  max-height: 200px;
  overflow-y: auto;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}
.constituent-option {
  padding: 6px 10px;
  cursor: pointer;
  font-size: 0.875rem;
}
.constituent-option:hover {
  background: #f0f4ff;
}
</style>
