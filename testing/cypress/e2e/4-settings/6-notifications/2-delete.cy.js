describe("Wizarr - Settings - Notifications - Delete", () => {
    it("tests Wizarr - Settings - Notifications - Delete", () => {
      cy.viewport(1466, 1162);
      cy.visit("http://127.0.0.1:9999/admin/settings/notifications");
      cy.wait(500);
      cy.get("tr:nth-of-type(1) svg").click();
      cy.wait(500);
      cy.get("tr:nth-of-type(1) button.bg-primary").click();
      cy.wait(500);
      cy.get("#delete-modal button.bg-primary").click();
    });
  });
  