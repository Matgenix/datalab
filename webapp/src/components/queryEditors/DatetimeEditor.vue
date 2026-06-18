<template>
  <div class="dt-editor">
    <input
      :value="datePart"
      type="date"
      class="qeditor-input"
      @input="onDate($event.target.value)"
    />
    <input
      :value="timePart"
      type="time"
      class="qeditor-input qeditor-input--time"
      @input="onTime($event.target.value)"
    />
  </div>
</template>

<script>
export default {
  name: "DatetimeEditor",
  props: {
    modelValue: { type: String, default: "" },
  },
  emits: ["update:modelValue"],
  data() {
    return { localTime: "" };
  },
  computed: {
    datePart() {
      return this.modelValue ? this.modelValue.split("T")[0] : "";
    },
    timePart() {
      if (!this.modelValue || !this.modelValue.includes("T")) return this.localTime;
      return this.modelValue.split("T")[1]?.substring(0, 5) || "";
    },
  },
  methods: {
    onDate(date) {
      const time = this.timePart || this.localTime || "00:00";
      this.$emit("update:modelValue", date ? `${date}T${time}` : "");
    },
    onTime(time) {
      this.localTime = time;
      if (this.datePart) {
        this.$emit("update:modelValue", `${this.datePart}T${time}`);
      }
    },
  },
};
</script>

<style scoped>
.dt-editor {
  display: flex;
  gap: 6px;
  align-items: center;
}
.qeditor-input {
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 3px 6px;
  font-size: 0.875rem;
  color: #374151;
  outline: none;
  background: transparent;
  min-width: 0;
  flex: 1;
}
.qeditor-input:focus {
  border-color: #6366f1;
}
.qeditor-input--time {
  flex: 0 0 84px;
}
</style>
