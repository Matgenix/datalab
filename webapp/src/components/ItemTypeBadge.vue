<template>
  <StyledTooltip :delay="500">
    <template #anchor>
      <span
        class="badge badge-pill item-type-badge"
        :style="badgeStyle"
        :aria-label="`${title} item type details`"
        data-testid="item-type-badge"
        tabindex="0"
      >
        {{ title }}
      </span>
    </template>
    <template #content>
      <h4 class="tooltip-title">{{ title }}</h4>
      <p class="type-classification">
        {{ isBuiltin ? "Datalab built-in item type" : "Custom item type" }}
      </p>
      <p>
        Identifier: <code class="type-identifier">{{ type }}</code>
      </p>
      <p v-if="!isBuiltin && itemType.baseType">
        Base type: <code class="type-identifier">{{ itemType.baseType }}</code>
      </p>
      <p v-if="itemType.description" class="type-description">{{ itemType.description }}</p>
    </template>
  </StyledTooltip>
</template>

<script>
import { itemTypes, itemTypeTitle } from "@/resources.js";
import StyledTooltip from "@/components/StyledTooltip.vue";

export default {
  name: "ItemTypeBadge",
  components: { StyledTooltip },
  props: {
    type: {
      type: String,
      required: true,
    },
  },
  computed: {
    itemType() {
      return itemTypes[this.type] || {};
    },
    title() {
      return itemTypeTitle(this.type);
    },
    isBuiltin() {
      return this.itemType.isBuiltin ?? !this.itemType.isDynamic;
    },
    badgeStyle() {
      return {
        backgroundColor: this.itemType.lightColor || "#e9ecef",
        color: this.itemType.labelColor || "#495057",
      };
    },
  },
};
</script>

<style scoped>
.item-type-badge {
  cursor: help;
  font-size: 0.85em;
  font-weight: 500;
}

.item-type-badge:focus-visible {
  outline: 2px solid cornflowerblue;
  outline-offset: 2px;
}

.type-classification {
  color: #ccc;
  font-size: 0.85em;
  font-style: italic;
}

.type-identifier {
  color: white;
  font-family: var(--font-monospace);
}

.type-description {
  margin-top: 0.5em;
}
</style>
