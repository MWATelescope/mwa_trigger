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
Cypress.Commands.add('login', () => {
    return cy.request({
      url: '/accounts/login/',
      // cookies are in the HTTP headers, so HEAD suffices
    }).then(() => {
  
      cy.getCookie('sessionid').should('not.exist')
      cy.getCookie('csrftoken').its('value').then((token) => {
        let oldToken = token
        console.log
        cy.request({
          url: '/accounts/login/',
          method: 'POST',
          form: true,
          followRedirect: false, // no need to retrieve the page after login
          body: {
            username: Cypress.env('UPLOAD_USER'),
            password: Cypress.env('UPLOAD_PASSWORD'),
            csrfmiddlewaretoken: token
          }
        }).then(() => {
  
          cy.getCookie('sessionid').should('exist')
          return cy.getCookie('csrftoken').its('value')
  
        })
      })
    })
  
  })
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