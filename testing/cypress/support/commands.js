// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
//
// -- This is a parent command --
// Cypress.Commands.add('login', (email, password) => { ... })
//
//
// -- This is a child command --
// Cypress.Commands.add('drag', { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add('dismiss', { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This will overwrite an existing command --
// Cypress.Commands.overwrite('visit', (originalFn, url, options) => { ... })

Cypress.Commands.add("login", () => {

    // create user if it doesn't exist
    cy.exec('python3 ../manage.py create_user --username cypress --password cypress --email cypress@example.com"', { failOnNonZeroExit: false }).then((manage_result) => {
        cy.log(manage_result.stdout.includes("created user") ? "User created" : "User already exists")
    });

    // make api call to get csrf token
    cy.request({
        method: 'POST',
        url: 'http://127.0.0.1:9999/api/auth/login',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: {
            username: 'cypress',
            password: 'cypress'
        }
    }).then((response) => {
        // log the response body
        cy.log(response.body)
        // log the status code
        cy.log(response.status)
    })

})

Cypress.Commands.add("logout", () => {

    cy.getCookie('csrf_access_token').then((cookie) => {
        // make api call to logout
        cy.request({
            method: 'POST',
            url: 'http://127.0.0.1:9999/api/auth/logout',
            headers: {
                "X-CSRF-TOKEN": cookie.value,
            },
        }).then((response) => {
            // log the response body
            cy.log(response.body)
            // log the status code
            cy.log(response.status)
        })
    })

    cy.visit('http://127.0.0.1:9999/login')

    // delete user
    cy.exec('python3 ../manage.py delete_user --username cypress --y true', { failOnNonZeroExit: false }).then((manage_result) => {
        cy.log(manage_result.stdout.includes("deleted user") ? "User deleted" : "User already deleted")
    });
})