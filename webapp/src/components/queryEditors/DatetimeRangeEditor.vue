<template>
  <div class="dt-range">
    <div class="dt-range__row">
      <span class="dt-range__label">From</span>
      <input
        :value="fromDate"
        type="date"
        class="qeditor-input"
        @input="onFromDate($event.target.value)"
      />
      <input
        :value="fromTime"
        type="time"
        class="qeditor-input qeditor-input--time"
        @input="onFromTime($event.target.value)"
      />
    </div>
    <div class="dt-range__row">
      <span class="dt-range__label">To</span>
      <input
        :value="toDate"
        type="date"
        class="qeditor-input"
        @input="onToDate($event.target.value)"
      />
      <input
        :value="toTime"
        type="time"
        class="qeditor-input qeditor-input--time"
        @input="onToTime($event.target.value)"
      />
    </div>
  </div>
</template>

<script>
function splitIso(iso) {
  if (!iso || !iso.includes("T")) return [iso || "", ""];
  const [d, t] = iso.split("T");
  return [d, t.substring(0, 5)];
}

export default {
  name: "DatetimeRangeEditor",
  props: {
    modelValue: { type: Array, default: () => ["", ""] },
  },
  emits: ["update:modelValue"],
  data() {
    return { fromLocalTime: "", toLocalTime: "" };
  },
  computed: {
    fromDate() {
      return splitIso(this.modelValue?.[0])[0];
    },
    fromTime() {
      return splitIso(this.modelValue?.[0])[1] || this.fromLocalTime;
    },
    toDate() {
      return splitIso(this.modelValue?.[1])[0];
    },
    toTime() {
      return splitIso(this.modelValue?.[1])[1] || this.toLocalTime;
    },
  },
  methods: {
    onFromDate(date) {
      const time = this.fromTime || this.fromLocalTime || "00:00";
      const from = date ? `${date}T${time}` : "";
      this.$emit("update:modelValue", [from, this.modelValue?.[1] || ""]);
    },
    onFromTime(time) {
      this.fromLocalTime = time;
      if (this.fromDate) {
        this.$emit("update:modelValue", [`${this.fromDate}T${time}`, this.modelValue?.[1] || ""]);
      }
    },
    onToDate(date) {
      const time = this.toTime || this.toLocalTime || "23:59";
      const to = date ? `${date}T${time}` : "";
      this.$emit("update:modelValue", [this.modelValue?.[0] || "", to]);
    },
    onToTime(time) {
      this.toLocalTime = time;
      if (this.toDate) {
        this.$emit("update:modelValue", [this.modelValue?.[0] || "", `${this.toDate}T${time}`]);
      }
    },
  },
};
</script>

<style scoped>
.dt-range {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.dt-range__row {
  display: flex;
  align-items: center;
  gap: 5px;
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
  flex: 1;
  min-width: 0;
}
.qeditor-input:focus {
  border-color: #6366f1;
}
.qeditor-input--time {
  flex: 0 0 84px;
}
</style>
