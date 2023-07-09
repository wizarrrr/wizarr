describe("Wizarr - Settings - Notifications - Delete", () => {
  it("tests Wizarr - Settings - Notifications - Delete", () => {
    cy.viewport(1466, 1162);
    cy.visit("http://127.0.0.1:5000/admin/invite");
    cy.get("li:nth-of-type(4) > button").click();
    cy.get("li:nth-of-type(7) > button").click();
    cy.get("tr:nth-of-type(1) svg").click();
    cy.get("tr:nth-of-type(1) button.bg-primary").click();
    cy.get("#delete-modal button.bg-primary").click();
  });
});
