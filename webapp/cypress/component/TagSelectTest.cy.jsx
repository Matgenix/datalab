import TagSelect from "@/components/TagSelect.vue";

describe("TagSelect.vue", () => {
  const managedTag = {
    type: "tags",
    immutable_id: "0123456789ab0123456789ab",
    name: "test-managed-tag",
    description: "reacts with air",
    color: "#f1c40f",
    scope: "global",
  };

  beforeEach(() => {
    cy.intercept("GET", "**/search-tags*", {
      body: { status: "success", data: [managedTag] },
    }).as("searchTags");
  });

  it("searches and emits a reference object when a managed tag is selected", () => {
    cy.mount(TagSelect, {
      props: { modelValue: [], "onUpdate:modelValue": cy.spy().as("update") },
    });

    cy.get(".vs__search").type("test-man");
    cy.wait("@searchTags");
    // The option shows the scope badge and a color swatch.
    cy.get(".vs__dropdown-option").contains("test-managed-tag").should("exist");
    cy.get(".vs__dropdown-option .badge").should("contain", "global");
    cy.get(".vs__dropdown-option .color-swatch").should("exist");
    cy.get(".vs__dropdown-option").contains("test-managed-tag").click();

    // The reference preserves display fields (color/description) but never `scope`.
    cy.get("@update").should("have.been.calledWith", [
      {
        type: "tags",
        immutable_id: managedTag.immutable_id,
        name: "test-managed-tag",
        color: "#f1c40f",
        description: "reacts with air",
      },
    ]);
  });

  it("emits a plain string when a free-text tag is created", () => {
    cy.mount(TagSelect, {
      props: { modelValue: [], "onUpdate:modelValue": cy.spy().as("update") },
    });

    cy.get(".vs__search").type("test-free-text-tag");
    cy.wait("@searchTags");
    // The typed value, not matching a managed tag, is offered as a free-text tag.
    cy.get(".vs__dropdown-option").contains("test-free-text-tag").click();

    cy.get("@update").should("have.been.calledWith", ["test-free-text-tag"]);
  });

  it("renders existing string and reference tags as selected chips", () => {
    cy.mount(TagSelect, {
      props: { modelValue: ["test-free-text-tag", managedTag] },
    });

    cy.get(".vs__selected").should("contain", "test-free-text-tag");
    cy.get(".vs__selected").should("contain", "test-managed-tag");
  });

  it("keeps a same-named tag from another scope available after one is selected", () => {
    // Two distinct managed tags share a name but differ in scope/immutable_id.
    const ownerTag = {
      type: "tags",
      immutable_id: "0123456789ab0123456789ab",
      name: "shared-name",
      scope: "owner",
    };
    const globalTag = {
      type: "tags",
      immutable_id: "ffffffffffffffffffffffff",
      name: "shared-name",
      scope: "global",
    };
    cy.intercept("GET", "**/search-tags*", {
      body: { status: "success", data: [ownerTag, globalTag] },
    }).as("searchTagsScoped");

    cy.mount(TagSelect, {
      props: { modelValue: [ownerTag], "onUpdate:modelValue": cy.spy().as("update") },
    });

    cy.get(".vs__search").type("shared");
    cy.wait("@searchTagsScoped");

    // The owner-scope tag is already selected and hidden, but the distinct
    // global-scope tag with the same name must still be offered.
    cy.get(".vs__dropdown-option").contains("shared-name").should("exist");
    cy.get(".vs__dropdown-option .badge").should("contain", "global");
    cy.get(".vs__dropdown-option .badge").should("not.contain", "owner");
  });

  it("labels a typed non-matching value as a free-text tag", () => {
    cy.mount(TagSelect, {
      props: { modelValue: [] },
    });

    cy.get(".vs__search").type("brand-new-tag");
    cy.wait("@searchTags");
    // The typed value (no managed match) is offered as a free-text tag.
    cy.get(".vs__dropdown-option .free-text-tag-hint").should("contain", "free-text");
  });
});
