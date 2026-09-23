import PrimeVue from "primevue/config";

import ItemTypeBadge from "@/components/ItemTypeBadge.vue";
import ItemTypeSelect from "@/components/ItemTypeSelect.vue";
import { itemTypes, registerDynamicItemType } from "@/resources.js";

const CUSTOM_TYPE = "example-mixed-solutions";
const SIMPLE_TYPE = "example-simple-items";
const SAMPLE_METADATA_KEYS = ["title", "description", "isBuiltin", "baseType"];
const originalSampleMetadata = Object.fromEntries(
  SAMPLE_METADATA_KEYS.map((key) => [key, itemTypes.samples[key]]),
);

function registerTypes() {
  registerDynamicItemType("samples", {
    title: "Sample",
    description: "A physical thing in the lab that can be characterised.",
    is_builtin: true,
  });
  registerDynamicItemType(CUSTOM_TYPE, {
    title: "Mixed Solution",
    description: "A solution blended from other solutions by volume.",
    is_builtin: false,
    base_type: "samples",
    ui_color: "#b5651d",
  });
}

describe("ItemTypeBadge", () => {
  beforeEach(registerTypes);

  afterEach(() => {
    delete itemTypes[CUSTOM_TYPE];
    delete itemTypes[SIMPLE_TYPE];
    for (const key of SAMPLE_METADATA_KEYS) {
      if (originalSampleMetadata[key] === undefined) {
        delete itemTypes.samples[key];
      } else {
        itemTypes.samples[key] = originalSampleMetadata[key];
      }
    }
  });

  it("describes a Datalab built-in type on hover", () => {
    cy.mount(ItemTypeBadge, { props: { type: "samples" } });

    cy.get('[data-testid="item-type-badge"]')
      .should("contain.text", "Sample")
      .and("have.attr", "tabindex", "0")
      .trigger("mouseenter");

    cy.get('[data-testid="styled-tooltip"]')
      .should("be.visible")
      .within(() => {
        cy.contains("Sample").should("be.visible");
        cy.contains("Datalab built-in item type").should("be.visible");
        cy.contains("samples").should("be.visible");
        cy.contains("A physical thing in the lab").should("be.visible");
        cy.contains("Base type:").should("not.exist");
      });
  });

  it("describes a custom type and its base type on keyboard focus", () => {
    cy.mount(ItemTypeBadge, { props: { type: CUSTOM_TYPE } });

    cy.get('[data-testid="item-type-badge"]')
      .should("contain.text", "Mixed Solution")
      .and("have.attr", "style")
      .and("contain", "background-color");
    cy.get('[data-testid="item-type-badge"]').focus();

    cy.get('[data-testid="styled-tooltip"]')
      .should("be.visible")
      .within(() => {
        cy.contains("Custom item type").should("be.visible");
        cy.contains(CUSTOM_TYPE).should("be.visible");
        cy.contains("Base type:").should("be.visible");
        cy.contains("samples").should("be.visible");
        cy.contains("A solution blended from other solutions by volume.").should("be.visible");
      });

    cy.get('[data-testid="item-type-badge"]').blur();
    cy.get('[data-testid="styled-tooltip"]').should("not.have.attr", "data-show");
  });

  it("omits optional custom metadata when it is absent", () => {
    registerDynamicItemType(SIMPLE_TYPE, { title: "Simple Item", is_builtin: false });

    cy.mount(ItemTypeBadge, { props: { type: SIMPLE_TYPE } });
    cy.get('[data-testid="item-type-badge"]').trigger("mouseenter");
    cy.get('[data-testid="styled-tooltip"]').within(() => {
      cy.contains("Custom item type").should("be.visible");
      cy.contains("Base type:").should("not.exist");
      cy.get(".type-description").should("not.exist");
    });
  });

  it("renders badges for the selected value and available type options", () => {
    const onUpdate = cy.stub().as("typeUpdated");
    cy.mount(ItemTypeSelect, {
      props: {
        modelValue: "samples",
        types: ["samples", CUSTOM_TYPE],
        inputId: "type-select",
        required: true,
        "onUpdate:modelValue": onUpdate,
      },
      global: { plugins: [PrimeVue] },
    });

    cy.get(".p-select").should("contain.text", "Sample").and("have.attr", "required");
    cy.get(".p-select").click();
    cy.get(".p-select").find(".p-select-overlay").should("be.visible");
    cy.get(".p-select-option").should("have.length", 2);
    cy.get(".p-select-option").contains("Mixed Solution").click();
    cy.get("@typeUpdated").should("have.been.calledWith", CUSTOM_TYPE);
  });

  it("preserves the disabled selector state", () => {
    cy.mount(ItemTypeSelect, {
      props: {
        modelValue: "samples",
        types: ["samples"],
        inputId: "type-select",
        disabled: true,
      },
      global: { plugins: [PrimeVue] },
    });

    cy.get(".p-select").should("have.class", "p-disabled").and("contain.text", "Sample");
  });
});
