<template>
  <div v-if="customFields.length > 0" class="container custom-fields-panel mt-3">
    <div class="plugin-card">
      <div
        v-if="sectionTitle"
        class="plugin-card-header d-flex align-items-center justify-content-between"
      >
        <span>{{ sectionTitle }}</span>
        <slot name="header-actions" />
      </div>
      <hr v-else class="mt-0" />
      <div class="plugin-card-body">
        <!-- Scalar fields: ref selectors, numbers, strings, enums, booleans -->
        <div v-if="scalarFields.length > 0" class="form-row mb-2">
          <div v-for="field in scalarFields" :key="field.name" class="form-group col-md-6 col-lg-4">
            <label :for="'custom-' + field.name">{{ field.title }}</label>

            <!-- Read-only -->
            <div v-if="field.readOnly" class="form-control-plaintext">
              {{ itemData[field.name] ?? "—" }}
            </div>

            <!-- Item reference: fixed link when selected, dropdown when empty -->
            <div v-else-if="field.refTypes">
              <div v-if="itemData[field.name]" class="input-group">
                <router-link
                  :to="`/edit/${itemData[field.name].item_id}`"
                  class="form-control ref-display"
                >
                  <span class="badge badge-secondary mr-2">{{
                    itemData[field.name].refcode || itemData[field.name].item_id
                  }}</span>
                  {{ itemData[field.name].name || "" }}
                </router-link>
                <div class="input-group-append">
                  <button
                    type="button"
                    class="btn btn-outline-secondary"
                    title="Clear"
                    @click="updateField(field.name, null)"
                  >
                    <font-awesome-icon :icon="['fas', 'times']" />
                  </button>
                </div>
              </div>
              <ItemSelect
                v-else
                :model-value="itemData[field.name]"
                :types-to-query="field.refTypes"
                @update:model-value="updateField(field.name, $event)"
              />
            </div>

            <!-- Number with unit selector -->
            <div
              v-else-if="(field.type === 'number' || field.type === 'integer') && field.unitField"
              class="input-group"
            >
              <input
                :id="'custom-' + field.name"
                type="number"
                class="form-control"
                :step="field.type === 'integer' ? '1' : 'any'"
                :value="itemData[field.name] ?? ''"
                @change="
                  updateField(
                    field.name,
                    $event.target.value === '' ? null : Number($event.target.value),
                  )
                "
              />
              <div class="input-group-append">
                <select
                  class="form-control unit-select"
                  :value="itemData[field.unitField] ?? field.defaultUnit"
                  @change="updateField(field.unitField, $event.target.value)"
                >
                  <option v-for="u in field.unitOptions" :key="u" :value="u">{{ u }}</option>
                </select>
              </div>
            </div>

            <!-- Enum → select -->
            <select
              v-else-if="field.enum"
              :id="'custom-' + field.name"
              class="form-control"
              :value="itemData[field.name] ?? ''"
              @change="updateField(field.name, $event.target.value || null)"
            >
              <option value="">—</option>
              <option v-for="opt in field.enum" :key="opt" :value="opt">{{ opt }}</option>
            </select>

            <!-- Boolean → checkbox -->
            <div v-else-if="field.type === 'boolean'" class="form-check mt-2">
              <input
                :id="'custom-' + field.name"
                type="checkbox"
                class="form-check-input"
                :checked="itemData[field.name]"
                @change="updateField(field.name, $event.target.checked)"
              />
            </div>

            <!-- Plain number -->
            <input
              v-else-if="field.type === 'number' || field.type === 'integer'"
              :id="'custom-' + field.name"
              type="number"
              class="form-control"
              :step="field.type === 'integer' ? '1' : 'any'"
              :value="itemData[field.name] ?? ''"
              @change="
                updateField(
                  field.name,
                  $event.target.value === '' ? null : Number($event.target.value),
                )
              "
            />

            <!-- String (default) -->
            <input
              v-else
              :id="'custom-' + field.name"
              type="text"
              class="form-control"
              :value="itemData[field.name] ?? ''"
              @change="updateField(field.name, $event.target.value || null)"
            />
          </div>
        </div>

        <!-- Constituent tables: always below scalar fields, full width -->
        <div v-for="field in tableFields" :key="field.name" class="mb-3 table-wrapper">
          <div class="d-flex align-items-center justify-content-between mb-1">
            <label class="mb-0">{{ field.title }}</label>
            <slot :name="`table-actions-${field.name}`" />
          </div>
          <CustomConstituentTable
            :model-value="itemData[field.name] || []"
            :types-to-query="field.typesToQuery"
            :unit-options="field.constituentUnitOptions"
            :default-unit="field.constituentDefaultUnit"
            :quantity-field="field.constituentQuantityField"
            :quantity-label="field.constituentQuantityLabel"
            :extra-columns="field.constituentExtraColumns"
          />
        </div>
      </div>
      <!-- plugin-card-body -->
    </div>
    <!-- plugin-card -->
  </div>
</template>

<script>
import { itemTypes, prettifyType } from "@/resources.js";
import ItemSelect from "@/components/ItemSelect.vue";
import CustomConstituentTable from "./CustomConstituentTable.vue";

// Pydantic v2 emits nullable fields as anyOf: [{type: X}, {type: "null"}].
function unwrapNullable(schema) {
  if (!schema) return { schema: {}, nullable: false };
  if (schema.anyOf) {
    const nonNull = schema.anyOf.filter((s) => s.type !== "null");
    if (nonNull.length === 1) {
      return { schema: { ...schema, ...nonNull[0], anyOf: undefined }, nullable: true };
    }
  }
  return { schema, nullable: false };
}

// Resolve a JSON Schema $ref against the type's $defs map.
function resolveRef(ref, defs) {
  if (!ref || !defs) return {};
  const name = ref.replace(/^#\/\$defs\//, "");
  return defs[name] || {};
}

function resolveField(name, rawSchema, defs) {
  const { schema } = unwrapNullable(rawSchema);
  const extra = rawSchema["x-json_schema_extra"] || rawSchema;
  const widget = extra.datalab_widget || null;

  // Constituent table: prefer explicit annotation (units/default_unit on the list field,
  // like the voltage pattern) over schema inference — avoids fragile $ref resolution.
  const BASE_CONSTITUENT_FIELDS = new Set(["item", "quantity", "unit"]);
  let typesToQuery = null;
  let constituentUnitOptions = null;
  let constituentDefaultUnit = "g";
  let constituentQuantityField = "quantity";
  let constituentQuantityLabel = "Quantity";
  let constituentExtraColumns = [];
  if (widget === "constituent-table") {
    typesToQuery = extra.datalab_constituent_types || ["samples", "starting_materials"];
    // Always resolve the items sub-schema — needed for extra columns.
    const itemsRaw = schema.items || {};
    const itemsSchema = itemsRaw.$ref ? resolveRef(itemsRaw.$ref, defs) : itemsRaw;
    if (extra.units) {
      // Explicit annotation: units listed directly on the field (preferred).
      constituentUnitOptions = extra.units;
    } else {
      // Fallback: infer from the items sub-schema's unit field enum.
      const unitRaw = itemsSchema.properties?.unit || {};
      const { schema: unitSchema } = unwrapNullable(unitRaw);
      constituentUnitOptions = unitSchema.enum || null;
    }
    constituentDefaultUnit = extra.default_unit || constituentUnitOptions?.[0] || "g";
    if (extra.datalab_quantity_field) {
      constituentQuantityField = extra.datalab_quantity_field;
      const qSchema = itemsSchema.properties?.[constituentQuantityField] || {};
      constituentQuantityLabel = qSchema.title || constituentQuantityField;
    }
    // Extra columns: properties beyond base Constituent fields and the quantity field.
    constituentExtraColumns = Object.entries(itemsSchema.properties || {})
      .filter(([colName, colRawSchema]) => {
        if (BASE_CONSTITUENT_FIELDS.has(colName)) return false;
        if (colName === constituentQuantityField) return false;
        const colExtra = colRawSchema["x-json_schema_extra"] || colRawSchema;
        if (colExtra.datalab_hidden) return false;
        return true;
      })
      .map(([colName, colRawSchema]) => {
        const { schema: colSchema } = unwrapNullable(colRawSchema);
        const extra = colRawSchema["x-json_schema_extra"] || colRawSchema;
        return {
          name: colName,
          title: colRawSchema.title || prettifyType(colName),
          type: colSchema.type || "string",
          description: colRawSchema.description || null,
          readOnly: extra.readOnly === true,
        };
      });
  }

  return {
    name,
    title: rawSchema.title || prettifyType(name),
    description: rawSchema.description || null,
    type: schema.type || "string",
    enum: schema.enum || null,
    readOnly: rawSchema.readOnly === true,
    widget,
    typesToQuery,
    constituentUnitOptions,
    constituentDefaultUnit,
    constituentQuantityField,
    constituentQuantityLabel,
    constituentExtraColumns,
    refTypes: extra.datalab_ref_types || null,
    // Number+unit compound widget
    unitField: extra.datalab_unit_field || null,
    unitOptions: extra.units || null,
    defaultUnit: extra.default_unit || null,
  };
}

export default {
  name: "CustomFieldsPanel",
  components: { ItemSelect, CustomConstituentTable },
  props: {
    item_id: { type: String, required: true },
    itemType: { type: String, required: true },
  },
  computed: {
    itemData() {
      return this.$store.state.all_item_data[this.item_id] || {};
    },
    typeEntry() {
      return itemTypes[this.itemType];
    },
    typeSchema() {
      return this.$store.state.schemas[this.itemType]?.attributes?.schema || null;
    },
    baseType() {
      return this.typeSchema?.datalab_base_type || this.typeEntry?.baseType || null;
    },
    baseSchema() {
      return this.baseType
        ? this.$store.state.schemas[this.baseType]?.attributes?.schema || null
        : null;
    },
    sectionTitle() {
      return this.typeSchema?.datalab_section_title || null;
    },
    scalarFields() {
      return this.customFields.filter((f) => f.widget !== "constituent-table");
    },
    tableFields() {
      return this.customFields.filter((f) => f.widget === "constituent-table");
    },
    customFields() {
      if (!this.typeSchema || !this.baseSchema) return [];
      const typeProps = this.typeSchema.properties || {};
      const defs = this.typeSchema.$defs || {};
      const baseProps = this.baseSchema ? Object.keys(this.baseSchema.properties || {}) : [];

      return Object.entries(typeProps)
        .filter(([name, schema]) => {
          if (baseProps.includes(name) || name === "type") return false;
          const extra = schema["x-json_schema_extra"] || schema;
          if (extra.datalab_hidden) return false;
          return true;
        })
        .map(([name, schema]) => resolveField(name, schema, defs));
    },
  },
  methods: {
    updateField(fieldName, value) {
      this.$store.commit("updateItemData", {
        item_id: this.item_id,
        item_data: { [fieldName]: value },
      });
    },
  },
};
</script>

<style scoped>
.custom-fields-panel {
  padding-bottom: 1rem;
}
.plugin-card {
  border: 1px solid #dee2e6;
  border-radius: 0.375rem;
  transition:
    box-shadow 0.15s ease,
    border-color 0.15s ease;
}
.plugin-card:hover {
  border-color: #adb5bd;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.07);
}
.plugin-card-header {
  font-size: 1rem;
  font-weight: 600;
  color: #495057;
  padding: 0.65rem 1rem;
  background-color: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
  border-radius: 0.375rem 0.375rem 0 0;
}
.plugin-card-body {
  padding: 1rem;
}
.table-wrapper {
  padding-left: 2.5rem;
}
.unit-select {
  border-left: 0;
  border-radius: 0 0.25rem 0.25rem 0;
  width: auto;
  min-width: 4.5rem;
}
.ref-display {
  display: flex;
  align-items: center;
  background-color: #f8f9fa;
  color: inherit;
  text-decoration: none;
  cursor: pointer;
  flex: 1;
}
.ref-display:hover {
  background-color: #e9ecef;
  text-decoration: none;
  color: inherit;
}
</style>
