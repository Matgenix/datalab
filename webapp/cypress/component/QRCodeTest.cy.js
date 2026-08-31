import { createStore } from "vuex";

import QRCode from "@/components/QRCode.vue";
import { makeQRCode } from "@/label_printing.js";

const mountQRCode = (serverInfo = null) => {
  const store = createStore({ state: { serverInfo, currentUserID: null } });
  cy.intercept("GET", "**/access-token-info", { statusCode: 404, body: {} });
  cy.mount(QRCode, {
    props: { refcode: "test:ABCDEF" },
    global: { plugins: [store], stubs: { FontAwesomeIcon: true } },
  });
};

describe("QR code label printing", () => {
  beforeEach(() => localStorage.removeItem("datalab-label-profile"));

  it("generates an SVG with a four-module quiet zone", () => {
    const qrCode = makeQRCode("https://example.com/test");
    const svg = decodeURIComponent(qrCode.image.split(",")[1]);

    expect(svg).to.contain(`viewBox="0 0 ${qrCode.modules} ${qrCode.modules}"`);
  });

  it("offers built-in formats and remembers the browser selection", () => {
    mountQRCode();

    cy.findByLabelText("Label format").should("have.value", "a4-single");
    cy.findByLabelText("Label format").select("tape-24mm");
    cy.wrap(localStorage).invoke("getItem", "datalab-label-profile").should("equal", "tape-24mm");
  });

  it("uses a deployment default and warns when its QR is too dense", () => {
    mountQRCode({
      label_printing: {
        default_profile: "tiny-label",
        profiles: [
          {
            id: "tiny-label",
            name: "Tiny label",
            media_type: "continuous",
            width_mm: 4,
            printable_width_mm: 2,
            dpi: 100,
            max_qr_size_mm: 2,
            alignment: "center",
            min_module_dots: 3,
          },
        ],
      },
    });

    cy.findByLabelText("Label format").should("have.value", "tiny-label");
    cy.get('[data-testid="qr-density-warning"]').should("be.visible");
    cy.contains("button", "Print anyway").should("be.enabled");
  });

  it("prints only the QR code and readable refcode, then cleans up", () => {
    cy.window().then((win) => cy.stub(win, "print"));
    mountQRCode();
    cy.contains("button", "Print label").click();
    cy.get("body > .qr-label-print").within(() => {
      cy.get("img").should("have.attr", "src").and("contain", "data:image/svg+xml");
      cy.get("div").should("have.text", "test:ABCDEF");
    });
    cy.get("body > style").last().should("contain.text", "@page { size: 210mm 297mm");
    cy.window().then((win) => win.dispatchEvent(new Event("afterprint")));
    cy.get("body > .qr-label-print").should("not.exist");
  });
});
