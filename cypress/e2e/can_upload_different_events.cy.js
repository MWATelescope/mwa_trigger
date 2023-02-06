
describe('Test other events can be uploaded', () => {
    it('upload Antares, Fermi, HESS, SWIFT test events', () => {
      const graceDBId = "MS33841s"
  
      cy.login()
      cy.visit('/')
  
      cy.fixture('Antares_ignore_observation_event.txt').then((event1) => {
        cy.get('[data-testid="nav-testing"]').click({ force: true })
        cy.get('[class="form-control"]').invoke('val', (event1))
        cy.get("[type='submit']").click()
      })
      cy.fixture('Fermi_ignore_observation_event.txt').then((event1) => {
        cy.get('[data-testid="nav-testing"]').click({ force: true })
        cy.get('[class="form-control"]').invoke('val', event1)
        cy.get("[type='submit']").click()
      })
      cy.fixture('HESS_promising_observation_event.txt').then((event1) => {
        cy.get('[data-testid="nav-testing"]').click({ force: true })
        cy.get('[class="form-control"]').invoke('val', event1)
        cy.get("[type='submit']").click()
      })
      cy.fixture('SWIFT_promising_observation_event.txt').then((event1) => {
        cy.get('[data-testid="nav-testing"]').click({ force: true })
        cy.get('[class="form-control"]').invoke('val', event1)
        cy.get("[type='submit']").click()
      })
    })
  })