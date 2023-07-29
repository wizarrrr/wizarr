describe("TEST", () => {
    it("tests 1", () => {
        cy.login()
        cy.wait(1000)
        cy.visit('http://127.0.0.1:9999/admin/settings/notifications')
        cy.wait(1000)
        cy.logout()
    });
});