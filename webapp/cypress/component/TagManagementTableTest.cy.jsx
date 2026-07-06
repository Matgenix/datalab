import TagManagementTable from "@/components/TagManagementTable.vue";
import UserBubble from "@/components/UserBubble.vue";
import StyledTooltip from "@/components/StyledTooltip.vue";
import PrimeVue from "primevue/config";
import { createStore } from "vuex";

describe("TagManagementTable Component Tests", () => {
  let store;

  beforeEach(() => {
    store = createStore({
      state() {
        return {
          currentUserID: "self",
          currentUserRole: "user",
          datatablePaginationSettings: {
            tags: { page: 0, rows: 20 },
          },
          tag_list: [
            {
              immutable_id: "t1",
              type: "tags",
              name: "flammable",
              description: "burns",
              color: "#f1c40f",
              creator_ids: ["self"],
              group_ids: [],
              creators: [{ immutable_id: "self", display_name: "Me" }],
              groups: [],
              editable: true,
            },
            {
              immutable_id: "t2",
              type: "tags",
              name: "global-tag",
              description: null,
              color: null,
              creator_ids: [],
              group_ids: [],
              creators: [],
              groups: [],
              editable: false,
            },
          ],
        };
      },
    });

    cy.mount(TagManagementTable, {
      global: {
        plugins: [store, PrimeVue],
        components: {
          UserBubble,
          StyledTooltip,
        },
      },
    });
  });

  it("renders the tag-specific toolbar buttons", () => {
    cy.get('[data-testid="add-tag-button"]').should("exist");
    cy.get('[data-testid="search-input"]').should("exist");
    cy.get('[data-testid="add-item-button"]').should("not.exist");
    cy.get('[data-testid="add-collection-button"]').should("not.exist");
  });

  it("renders the expected columns", () => {
    const headers = ["", "Tag", "Description", "Creators", "Actions"];
    cy.get(".p-datatable-column-header-content").should("have.length", headers.length);
    cy.get(".p-datatable-column-header-content").each((header, index) => {
      cy.wrap(header).should("contain.text", headers[index]);
    });
  });

  it("displays a colored badge per tag from the store", () => {
    cy.get(".p-datatable-tbody")
      .find("tr")
      .eq(0)
      .within(() => {
        cy.get("td").eq(1).find(".tag-badge").should("contain.text", "flammable");
      });
    cy.get(".p-datatable-tbody")
      .find("tr")
      .eq(1)
      .within(() => {
        cy.get("td").eq(1).find(".tag-badge").should("contain.text", "global-tag");
      });
  });

  it("shows Edit/Delete only for editable tags", () => {
    // Only the first tag is editable (the global one is not, for this non-admin user).
    cy.get('button[title="Edit tag"]').should("have.length", 1);
    cy.get('button[title="Delete tag"]').should("have.length", 1);

    cy.get(".p-datatable-tbody")
      .find("tr")
      .eq(0)
      .within(() => {
        cy.get('button[title="Edit tag"]').should("exist");
      });
    cy.get(".p-datatable-tbody")
      .find("tr")
      .eq(1)
      .within(() => {
        cy.get('button[title="Edit tag"]').should("not.exist");
        cy.get('button[title="Delete tag"]').should("not.exist");
      });
  });
});
