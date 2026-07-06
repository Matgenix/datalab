// E2e tests for the tag management page (/tags). Needs the dev server + API (:5001) running
// with testing auth, like the other e2e specs. The permission test relies on the same admin
// convention as authenticatedSampleTests.cy.js (admin-user@example.com is an admin).

const ownerEmail = "tag-owner@example.com";
const adminEmail = "admin-user@example.com";

describe("Tag management page", () => {
  // Names must not be substrings of each other: cy.contains matches substrings, so a
  // "not.exist" check on the original would still match the renamed badge otherwise.
  const tagName = "e2e-create-tag";
  const renamedTag = "e2e-renamed-tag";

  beforeEach(() => {
    cy.loginViaTestMagicLink(ownerEmail);
    cy.deleteTagByNameViaAPI(tagName);
    cy.deleteTagByNameViaAPI(renamedTag);
  });

  after(() => {
    cy.loginViaTestMagicLink(ownerEmail);
    cy.deleteTagByNameViaAPI(tagName);
    cy.deleteTagByNameViaAPI(renamedTag);
  });

  it("creates, edits and deletes a tag", () => {
    cy.visit("/tags");

    // Create
    cy.get('[data-testid="add-tag-button"]').click();
    cy.get("#tag-name").type(tagName);
    cy.get("#tag-description").type("created in an e2e test");
    cy.get(".swatch").first().click();
    cy.get(".modal-footer input[type=submit]:visible").click();
    cy.contains(".tag-badge", tagName).should("exist");

    // Edit (rename)
    cy.contains("tr", tagName).find('button[title="Edit tag"]').click();
    cy.get("#tag-name").clear();
    cy.get("#tag-name").type(renamedTag);
    cy.get(".modal-footer input[type=submit]:visible").click();
    cy.contains(".tag-badge", renamedTag).should("exist");
    cy.contains(".tag-badge", tagName).should("not.exist");

    // Delete
    cy.contains("tr", renamedTag).find('button[title="Delete tag"]').click();
    cy.get('[data-testid="dialog-modal-confirm-button"]').click();
    cy.contains(".tag-badge", renamedTag).should("not.exist");
  });
});

describe("Tag management permissions", () => {
  const globalTag = "e2e-global-tag";

  before(() => {
    // A global tag (empty creators) can only be created by an admin.
    cy.loginViaTestMagicLink(adminEmail);
    cy.deleteTagByNameViaAPI(globalTag);
    cy.createTagViaAPI({ name: globalTag, creator_ids: [] });
  });

  after(() => {
    cy.loginViaTestMagicLink(adminEmail);
    cy.deleteTagByNameViaAPI(globalTag);
  });

  it("hides edit/delete on a global tag for a non-owner", () => {
    cy.loginViaTestMagicLink(ownerEmail);
    cy.visit("/tags");
    cy.contains("tr", globalTag).should("exist");
    cy.contains("tr", globalTag).within(() => {
      cy.get('button[title="Edit tag"]').should("not.exist");
      cy.get('button[title="Delete tag"]').should("not.exist");
    });
  });

  it("shows edit/delete on a global tag for an admin", () => {
    cy.loginViaTestMagicLink(adminEmail);
    cy.visit("/tags");
    cy.contains("tr", globalTag).within(() => {
      cy.get('button[title="Edit tag"]').should("exist");
    });
  });
});

describe("Applying a tag to an item", () => {
  const intTag = "e2e-applied-tag";
  const sampleId = "e2e-tag-sample";

  beforeEach(() => {
    cy.loginViaTestMagicLink(ownerEmail);
    cy.deleteSampleViaAPI(sampleId);
    cy.deleteTagByNameViaAPI(intTag);
    cy.createTagViaAPI({ name: intTag });
    cy.visit("/samples");
    cy.createSample(sampleId, "Tag e2e sample");
  });

  after(() => {
    cy.loginViaTestMagicLink(ownerEmail);
    cy.deleteSampleViaAPI(sampleId);
    cy.deleteTagByNameViaAPI(intTag);
  });

  it("applies a managed tag and drops it from the item when the tag is deleted", () => {
    cy.intercept("GET", "**/search-tags*").as("searchTags");
    cy.intercept("POST", "**/save-item/").as("save");

    cy.visit(`/edit/${sampleId}`);

    // Enter edit mode on the Tags field (click the label text, away from the cog link),
    // then pick the managed tag from the TagSelect dropdown.
    cy.get("#tags").click("left");
    cy.get("#tags").parent().find(".vs__search").type(intTag);
    cy.wait("@searchTags");
    cy.get("#tags").parent().contains(".vs__dropdown-option", intTag).click();

    // Save (Ctrl/Cmd+S) and confirm the tag survives a reload.
    cy.get("body").type("{ctrl}s");
    cy.wait("@save");
    cy.reload();
    cy.contains(".tag-badge", intTag).should("exist");

    // Deleting the tag removes the reference from the item on the next read.
    cy.deleteTagByNameViaAPI(intTag);
    cy.reload();
    cy.contains(".tag-badge", intTag).should("not.exist");
  });
});
