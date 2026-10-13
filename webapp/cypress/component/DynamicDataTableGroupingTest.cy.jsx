import "bootstrap/dist/css/bootstrap.css";
import DynamicDataTableGroupingExample from "../fixtures/DynamicDataTableGroupingExample.vue";
import DatalabPreset from "@/primevue-theme-preset.js";
import PrimeVue from "primevue/config";
import { createStore } from "vuex";

const groupHeader = (label) => cy.contains('[data-testid="group-header"]', label);
const itemCells = (itemId) =>
  cy.get(".p-datatable-tbody td").filter((_, cell) => cell.textContent.trim() === itemId);

describe("DynamicDataTable grouping", () => {
  beforeEach(() => {
    window.localStorage.clear();

    const store = createStore({
      state: {
        currentUserID: null,
        datatablePaginationSettings: {
          groupingExample: { page: 0, rows: 20 },
        },
      },
      getters: {
        isAdminSuperUserModeActive: () => false,
      },
      mutations: {
        setPage(state, { type, page }) {
          state.datatablePaginationSettings[type].page = page;
        },
        setRows(state, { type, rows }) {
          state.datatablePaginationSettings[type].rows = rows;
        },
      },
    });

    cy.mount(DynamicDataTableGroupingExample, {
      global: {
        plugins: [store, [PrimeVue, { theme: DatalabPreset }]],
      },
    });
  });

  it("keeps the existing flat table when grouping is empty", () => {
    cy.get(".p-datatable").should("have.length", 1);
    cy.get('[data-testid="group-header"]').should("not.exist");
    cy.get(".p-datatable-tbody > tr").should("have.length", 4);
    cy.get(".p-datatable-tbody input[type='checkbox']").should("have.length", 4);
    cy.contains("td", /^item-1$/).should("have.length", 1);
    cy.contains("td", /^item-4$/).should("have.length", 1);
    cy.get(".p-paginator").should("exist");
  });

  it("expands nested tag and status groups in the same DataTable", () => {
    cy.get('[data-testid="group-by-tags-status"]').click();
    cy.get(".p-datatable").should("have.length", 1);

    groupHeader("Red").find('[data-testid="group-toggle"]').click();
    groupHeader("Active").should("exist");
    groupHeader("Active").find('[data-testid="group-toggle"]').click();

    cy.contains("td", /^item-1$/).should("have.length", 1);
    cy.contains("td", /^item-2$/).should("have.length", 1);
  });

  it("filters logical rows before placing them in every matching group", () => {
    cy.get('[data-testid="group-by-tags"]').click();
    cy.get('[data-testid="search-input"]').type("Alpha");

    groupHeader("Blue").should("contain.text", "1");
    groupHeader("Red").should("contain.text", "1");
    groupHeader("No Tags").should("not.exist");
  });

  it("selects a multi-tag item once across both appearances", () => {
    cy.get('[data-testid="group-by-tags"]').click();
    groupHeader("Blue").find('[data-testid="group-toggle"]').click();
    groupHeader("Red").find('[data-testid="group-toggle"]').click();

    itemCells("item-1").should("have.length", 2);
    itemCells("item-1").first().parents("tr").find("input[type='checkbox']").click({ force: true });

    itemCells("item-1")
      .parents("tr")
      .find("input[type='checkbox']")
      .should("have.length", 2)
      .and("be.checked");
    cy.get('[data-testid="selection-summary"]').should("contain.text", "1 item selected");

    cy.get('[data-testid="show-flat"]').click();
    cy.get(".p-datatable").should("have.length", 1);
    itemCells("item-1").parents("tr").find("input[type='checkbox']").should("be.checked");
  });

  it("selects visible duplicate occurrences once and restores flat select-all state", () => {
    cy.get('[data-testid="group-by-tags"]').click();
    groupHeader("Blue").find('[data-testid="group-toggle"]').click();
    groupHeader("Red").find('[data-testid="group-toggle"]').click();

    cy.get(".p-datatable-thead input[type='checkbox']").click({ force: true });
    cy.get('[data-testid="selection-summary"]').should("contain.text", "3 items selected");

    cy.get('[data-testid="show-flat"]').click();
    cy.get(".p-datatable-thead input[type='checkbox']").should("not.be.checked");
  });
});
