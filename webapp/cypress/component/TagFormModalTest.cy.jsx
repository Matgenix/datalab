import TagFormModal from "@/components/TagFormModal.vue";
import { createStore } from "vuex";

// Mount the modal closed, then open it by flipping `modelValue` so the Modal's open watcher
// (and the form's populate/reset watcher) fire as they do in the app. Returns the test-utils
// wrapper aliased as "wrapper" for setData / emitted assertions.
//
// Note: component tests run without the app's global Bootstrap CSS, so the Modal's backdrop
// overlays the dialog (no .modal z-index). We use { force: true } on interactions to bypass
// that purely-visual actionability check; the request-body and emit assertions are unaffected.
function mountAndOpen({ role = "user", userId = "self", tag = null } = {}) {
  const store = createStore({
    state() {
      return { currentUserRole: role, currentUserID: userId };
    },
  });
  return cy
    .mount(TagFormModal, {
      props: { modelValue: false, tag },
      global: { plugins: [store] },
    })
    .then(({ wrapper }) => {
      cy.wrap(wrapper).as("wrapper");
      return wrapper.setProps({ modelValue: true });
    });
}

describe("TagFormModal.vue", () => {
  describe("create mode", () => {
    it("creates a personal tag (no ownership fields in the payload)", () => {
      cy.intercept("PUT", "**/tags", { statusCode: 201, body: { status: "success", data: {} } }).as(
        "create",
      );
      mountAndOpen();

      cy.get("#tag-name").type("flammable", { force: true });
      cy.get('input[type="submit"]').click({ force: true });

      cy.wait("@create")
        .its("request.body")
        .should("deep.equal", {
          data: { name: "flammable", description: null, color: null },
        });
      cy.get("@wrapper").should((wrapper) => {
        expect(wrapper.emitted("tag-created")).to.have.length(1);
        // The modal asks its parent to close on success.
        expect(wrapper.emitted("update:modelValue").at(-1)).to.deep.equal([false]);
      });
    });

    it("adds the caller alongside any additional creators and groups", () => {
      cy.intercept("PUT", "**/tags", { statusCode: 201, body: { status: "success", data: {} } }).as(
        "create",
      );
      mountAndOpen({ userId: "self" });

      cy.get("#tag-name").type("shared", { force: true });
      // Drive the ownership selections directly rather than through vue-select.
      cy.get("@wrapper").then((wrapper) =>
        wrapper.setData({
          selectedCreators: [{ immutable_id: "user-2" }],
          shareWithGroups: [{ immutable_id: "group-1" }],
        }),
      );
      cy.get('input[type="submit"]').click({ force: true });

      cy.wait("@create")
        .its("request.body.data")
        .should("deep.equal", {
          name: "shared",
          description: null,
          color: null,
          creator_ids: ["self", "user-2"],
          group_ids: ["group-1"],
        });
    });

    it("creates a global tag when the admin checkbox is set", () => {
      cy.intercept("PUT", "**/tags", { statusCode: 201, body: { status: "success", data: {} } }).as(
        "create",
      );
      mountAndOpen({ role: "admin" });

      cy.get("#tag-name").type("global-tag", { force: true });
      cy.get("#tag-global").check({ force: true });
      cy.get('input[type="submit"]').click({ force: true });

      cy.wait("@create").its("request.body.data").should("deep.equal", {
        name: "global-tag",
        description: null,
        color: null,
        creator_ids: [],
      });
    });

    it("hides the Global checkbox for non-admins", () => {
      mountAndOpen({ role: "user" });
      cy.get("#tag-name").should("exist");
      cy.get("#tag-global").should("not.exist");
    });

    it("shows a name conflict (409) inline instead of an error dialog", () => {
      cy.intercept("PUT", "**/tags", {
        statusCode: 409,
        body: { status: "error", message: "A tag named 'dup' already exists in this scope." },
      }).as("create");
      mountAndOpen();

      cy.get("#tag-name").type("dup", { force: true });
      cy.get('input[type="submit"]').click({ force: true });

      cy.wait("@create");
      cy.get(".form-error").should("contain", "already exists");
      // The modal stays open on a conflict.
      cy.get("@wrapper").should((wrapper) => {
        expect(wrapper.emitted("tag-created")).to.be.undefined;
      });
    });
  });

  describe("edit mode", () => {
    const existingTag = {
      immutable_id: "tag-1",
      name: "old-name",
      description: "desc",
      color: "#abcdef",
      creator_ids: ["self"],
      group_ids: [],
      creators: [{ immutable_id: "self", display_name: "Me" }],
      groups: [],
    };

    it("pre-fills fields and updates only metadata when ownership is unchanged", () => {
      cy.intercept("PATCH", "**/tags/*", { statusCode: 200, body: { status: "success" } }).as(
        "updateTag",
      );
      cy.intercept("PATCH", "**/tags/*/permissions", {
        statusCode: 200,
        body: { status: "success" },
      }).as("updatePerms");
      mountAndOpen({ tag: existingTag });

      cy.get("#tag-name").should("have.value", "old-name");
      cy.get("#tag-name").clear({ force: true });
      cy.get("#tag-name").type("new-name", { force: true });
      cy.get('input[type="submit"]').click({ force: true });

      cy.wait("@updateTag").its("request.body.data.name").should("equal", "new-name");
      cy.get("@updatePerms.all").should("have.length", 0);
      cy.get("@wrapper").should((wrapper) => {
        expect(wrapper.emitted("tag-updated")).to.have.length(1);
      });
    });

    it("updates only permissions when ownership changes but metadata does not", () => {
      cy.intercept("PATCH", "**/tags/*", { statusCode: 200, body: { status: "success" } }).as(
        "updateTag",
      );
      cy.intercept("PATCH", "**/tags/*/permissions", {
        statusCode: 200,
        body: { status: "success" },
      }).as("updatePerms");
      mountAndOpen({ tag: existingTag });

      // Add a creator without touching name/description/color.
      cy.get("@wrapper").then((wrapper) =>
        wrapper.setData({
          selectedCreators: [
            { immutable_id: "self", display_name: "Me" },
            { immutable_id: "user-2", display_name: "Them" },
          ],
        }),
      );
      cy.get('input[type="submit"]').click({ force: true });

      cy.wait("@updatePerms")
        .its("request.body.creators")
        .should("deep.equal", [{ immutable_id: "self" }, { immutable_id: "user-2" }]);
      cy.get("@updateTag.all").should("have.length", 0);
    });
  });
});
