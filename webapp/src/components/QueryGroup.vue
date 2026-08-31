<template>
  <div class="qg" :class="{ 'qg--nested': currentDepth > 0 }">
    <div v-if="node.children.length > 1" class="qg__combinator">
      <button
        class="qg__comb-btn"
        :class="{ 'qg__comb-btn--active': node.combinator === 'and' }"
        @click="setCombinator('and')"
      >
        AND
      </button>
      <button
        class="qg__comb-btn"
        :class="{ 'qg__comb-btn--active': node.combinator === 'or' }"
        @click="setCombinator('or')"
      >
        OR
      </button>
    </div>

    <div class="qg__rules">
      <div v-for="(child, index) in node.children" :key="child._uid" class="qg__rule-wrap">
        <QueryRule
          v-if="child.kind === 'rule'"
          :node="child"
          :fields="fields"
          @update:node="updateChild(index, $event)"
          @remove="removeChild(index)"
        />
        <QueryGroup
          v-else
          :node="child"
          :fields="fields"
          :max-depth="maxDepth"
          :current-depth="currentDepth + 1"
          @update:node="updateChild(index, $event)"
          @remove="removeChild(index)"
        />
      </div>
    </div>

    <div class="qg__actions">
      <button class="qg__add-rule" @click="addRule">
        <font-awesome-icon icon="plus" class="me-1" />New Rule
      </button>
      <button v-if="currentDepth < maxDepth - 1" class="qg__add-group" @click="addGroup">
        Add group
      </button>
      <button v-if="currentDepth > 0" class="qg__remove-group ms-auto" @click="$emit('remove')">
        <font-awesome-icon icon="times" /> Remove group
      </button>
    </div>
  </div>
</template>

<script>
import QueryRule from "@/components/QueryRule.vue";

let uidCounter = 0;

export default {
  name: "QueryGroup",
  components: { QueryRule },
  props: {
    node: { type: Object, required: true },
    fields: { type: Array, required: true },
    maxDepth: { type: Number, default: 3 },
    currentDepth: { type: Number, default: 0 },
  },
  emits: ["update:node", "remove"],
  methods: {
    setCombinator(val) {
      this.$emit("update:node", { ...this.node, combinator: val });
    },
    addRule() {
      const firstField = this.fields[0];
      const firstOp = firstField?.operators[0]?.id || "";
      this.$emit("update:node", {
        ...this.node,
        children: [
          ...this.node.children,
          { kind: "rule", field: firstField?.id || "", operator: firstOp, _uid: ++uidCounter },
        ],
      });
    },
    addGroup() {
      this.$emit("update:node", {
        ...this.node,
        children: [
          ...this.node.children,
          { kind: "group", combinator: "and", children: [], _uid: ++uidCounter },
        ],
      });
    },
    updateChild(index, updated) {
      const children = [...this.node.children];
      children[index] = updated;
      this.$emit("update:node", { ...this.node, children });
    },
    removeChild(index) {
      this.$emit("update:node", {
        ...this.node,
        children: this.node.children.filter((_, i) => i !== index),
      });
    },
  },
};
</script>

<style scoped>
.qg {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.qg--nested {
  border-left: 3px solid #e5e7eb;
  padding-left: 14px;
  margin-top: 8px;
  padding-top: 8px;
}

.qg__combinator {
  display: flex;
  align-items: center;
  gap: 0;
  margin-bottom: 8px;
  align-self: flex-start;
}
.qg__comb-btn {
  padding: 3px 12px;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.1s;
  letter-spacing: 0.03em;
}
.qg__comb-btn:first-child {
  border-radius: 6px 0 0 6px;
}
.qg__comb-btn:last-child {
  border-radius: 0 6px 6px 0;
  border-left: none;
}
.qg__comb-btn--active {
  background: #6366f1;
  border-color: #6366f1;
  color: #fff;
}

.qg__rules {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.qg__rule-wrap {
  display: flex;
  flex-direction: column;
}

.qg__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  padding-top: 2px;
}
.qg__add-rule {
  background: none;
  border: none;
  color: #6366f1;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
}
.qg__add-rule:hover {
  color: #4f46e5;
}
.qg__add-group {
  background: none;
  border: 1px dashed #d1d5db;
  border-radius: 6px;
  color: #9ca3af;
  font-size: 0.78rem;
  cursor: pointer;
  padding: 2px 10px;
  transition:
    border-color 0.12s,
    color 0.12s;
}
.qg__add-group:hover {
  border-color: #6366f1;
  color: #6366f1;
}
.qg__remove-group {
  background: none;
  border: none;
  color: #f87171;
  font-size: 0.78rem;
  cursor: pointer;
  padding: 0;
  margin-left: auto;
}
.ms-auto {
  margin-left: auto;
}
</style>
