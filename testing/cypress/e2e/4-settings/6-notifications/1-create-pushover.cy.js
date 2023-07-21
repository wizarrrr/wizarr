describe("Wizarr - Settings - Notifications - Create - Pushover", () => {
  it("tests Wizarr - Settings - Notifications - Create - Pushover", () => {
    cy.viewport(1466, 1162);
    cy.visit("http://127.0.0.1:9999/admin/settings/notifications");
    cy.get("#create-agent-button").click();
    cy.get("#agent_name").click();
    cy.get("#agent_name").type("TEST");
    cy.wait(500);
    cy.get("#agent_service").eq(0).select("pushover");
    cy.wait(500);
    cy.get("#agent_username").click();
    cy.get("#agent_username").type("uLCnNuNPeE9t7KTvVbFv6fPejYw5WX");
    cy.wait(500);
    cy.get("#agent_password").click();
    cy.get("#agent_password").type("ai2xt7vpg44wssvkgk684psujgrg4f");
    cy.wait(500);
    cy.get("#settings-content > div:nth-of-type(1) button.bg-primary").click();
  });
});
