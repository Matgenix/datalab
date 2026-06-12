<template>
  <table class="table table-sm borderless" :style="{ width: tableWidth }">
    <colgroup>
      <col span="1" style="width: 320px" />
      <col span="1" style="width: 90px" />
      <col span="1" style="width: 95px" />
      <col v-for="col in extraColumns" :key="col.name" span="1" style="width: 110px" />
      <col span="1" style="width: 25px" />
    </colgroup>
    <thead>
      <tr class="table-header-row">
        <th class="text-muted small fw-normal">Compound</th>
        <th class="text-muted small fw-normal">{{ quantityLabel || "Quantity" }}</th>
        <th class="text-muted small fw-normal">Unit</th>
        <th v-for="col in extraColumns" :key="col.name" class="text-muted small fw-normal">
          {{ col.title }}
        </th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(constituent, index) in constituents" :key="index">
        <td>
          <ItemSelect
            v-if="selectShown[index]"
            :ref="`select${index}`"
            v-model="selectedChangedConstituent"
            class="select-in-row"
            :clearable="false"
            :types-to-query="typesToQuery"
            @option:selected="swapConstituent($event, index)"
            @search:blur="selectShown[index] = false"
          />
          <FormattedItemName
            v-else
            :item_id="constituent.item.item_id"
            :item-type="constituent.item.type"
            :name="constituent.item.name"
            :chemform="''"
            :smiles="constituent.item.smiles"
            :inchi-key="constituent.item.inchi_key"
            :ghs-codes="constituent.item.GHS_codes"
            :molar-mass="constituent.item.molar_mass"
            :cas="constituent.item.CAS"
            :max-length="35"
            enable-modified-click
            @dblclick="turnOnRowSelect(index)"
          />
        </td>
        <td>
          <input
            :value="constituent[quantityField] ?? ''"
            class="form-control form-control-sm quantity-input"
            :class="{ 'red-border': isNaN(constituent[quantityField]) }"
            type="number"
            step="any"
            placeholder="—"
            @change="
              constituent[quantityField] =
                $event.target.value === '' ? null : Number($event.target.value)
            "
          />
        </td>
        <td>
          <select
            v-if="unitOptions"
            v-model="constituent.unit"
            class="form-control form-control-sm"
          >
            <option v-for="u in unitOptions" :key="u" :value="u">{{ u }}</option>
          </select>
          <input
            v-else
            v-model="constituent.unit"
            class="form-control form-control-sm"
            placeholder="unit"
          />
        </td>
        <td v-for="col in extraColumns" :key="col.name">
          <span v-if="col.readOnly" class="form-control-plaintext form-control-sm text-muted">
            {{ constituent[col.name] ?? "—" }}
          </span>
          <input
            v-else-if="col.type === 'number' || col.type === 'integer'"
            :value="constituent[col.name] ?? ''"
            type="number"
            step="any"
            class="form-control form-control-sm"
            placeholder="—"
            @change="
              constituent[col.name] =
                $event.target.value === '' ? null : Number($event.target.value)
            "
          />
          <input
            v-else
            v-model="constituent[col.name]"
            type="text"
            class="form-control form-control-sm"
            placeholder="—"
          />
        </td>
        <td>
          <button
            type="button"
            class="close"
            aria-label="delete"
            @click.stop="removeConstituent(index)"
          >
            <span aria-hidden="true">&times;</span>
          </button>
        </td>
      </tr>
      <tr>
        <td
          class="first-column"
          :class="{ clickable: !newSelectIsShown }"
          @click="
            addNewConstituentIsActive = true;
            focusNewSelect();
          "
        >
          <transition name="fade">
            <font-awesome-icon
              v-if="!newSelectIsShown"
              class="add-row-button clickable"
              :icon="['far', 'plus-square']"
            />
          </transition>
          <span v-if="!newSelectIsShown">&nbsp;</span>
          <OnClickOutside v-if="newSelectIsShown" @trigger="addNewConstituentIsActive = false">
            <ItemSelect
              ref="newSelect"
              v-model="selectedNewConstituent"
              taggable
              :types-to-query="typesToQuery"
              @option:selected="addConstituent"
            />
          </OnClickOutside>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<script>
import ItemSelect from "@/components/ItemSelect";
import FormattedItemName from "@/components/FormattedItemName.vue";
import { OnClickOutside } from "@vueuse/components";

export default {
  name: "CustomConstituentTable",
  components: {
    ItemSelect,
    FormattedItemName,
    OnClickOutside,
  },
  props: {
    modelValue: {
      type: Array,
      default: () => [],
    },
    typesToQuery: {
      type: Array,
      default: () => ["samples", "starting_materials", "cells"],
    },
    unitOptions: {
      type: Array,
      default: null,
    },
    defaultUnit: {
      type: String,
      default: "g",
    },
    quantityField: {
      type: String,
      default: "quantity",
    },
    quantityLabel: {
      type: String,
      default: "Quantity",
    },
    extraColumns: {
      type: Array,
      default: () => [],
    },
  },
  emits: ["update:modelValue"],
  data() {
    return {
      selectedNewConstituent: null,
      selectedChangedConstituent: null,
      selectShown: [],
      addNewConstituentIsActive: false,
    };
  },
  computed: {
    tableWidth() {
      // 320 (compound) + 90 (qty) + 95 (unit) + 110*extra + 25 (delete)
      return 530 + this.extraColumns.length * 110 + "px";
    },
    newSelectIsShown() {
      return this.constituents.length == 0 || this.addNewConstituentIsActive;
    },
    constituents: {
      get() {
        if (!this.modelValue) {
          return [];
        }
        return this.modelValue;
      },
      set(value) {
        this.$emit("update:modelValue", value);
      },
    },
  },
  methods: {
    addConstituent(selectedItem) {
      const extraData = {};
      this.extraColumns.forEach((col) => {
        extraData[col.name] = null;
      });
      this.constituents.push({
        item: selectedItem,
        [this.quantityField]: null,
        unit: this.defaultUnit,
        ...extraData,
      });
      this.selectedNewConstituent = null;
      this.selectShown.push(false);
      this.addNewConstituentIsActive = false;
    },
    turnOnRowSelect(index) {
      this.selectShown[index] = true;
      this.selectedChangedConstituent = this.constituents[index].item;
      this.$nextTick(function () {
        this.$refs[`select${index}`]?.$refs?.selectComponent?.$refs?.search?.focus();
      });
    },
    swapConstituent(selectedItem, index) {
      this.constituents[index].item = selectedItem;
      this.selectShown[index] = false;
    },
    removeConstituent(index) {
      this.constituents.splice(index, 1);
      this.selectShown.splice(index, 1);
    },
    focusNewSelect() {
      this.$nextTick(() => {
        this.$refs["newSelect"].$refs.selectComponent.$refs.search.focus();
      });
    },
  },
};
</script>

<style scoped>
.table-header-row th {
  padding: 0 0.2rem 0.3rem 0.2rem;
  border-bottom: 1px solid #dee2e6;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

td {
  padding: 0.2rem !important;
}

.first-column {
  position: relative;
}

.add-row-button {
  position: absolute;
  font-size: regular;
  color: #bbb;
  float: right;
  transform: translateY(-50%);
  transition: transform 0.4s ease;
  width: 1.5rem;
  left: -2rem;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.select-in-row {
  width: 100%;
}

.borderless tr,
.borderless td {
  border: none !important;
}
</style>
