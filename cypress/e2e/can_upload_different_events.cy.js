
describe('Test other events can be uploaded', () => {
    it('upload Antares, Fermi, HESS, SWIFT test events', () => {
      const graceDBId = "MS33841s"
  
      cy.login()
      cy.visit('/')
      cy.wait(1000)
  
      //upload lvc "real" event that we want to trigger on
      cy.fixture('Antares_1438351269.txt').then((event1) => {
        cy.get('[data-testid="nav-testing"]').click({ force: true })
        cy.get('[class="form-control"]').invoke('val', (event1))
        cy.wait(1000)
        cy.get("[type='submit']").click()
        cy.wait(2000)
      })
      //upload lvc "real" event that we want to trigger on
      cy.fixture('Fermi00.txt').then((event1) => {
        cy.get('[data-testid="nav-testing"]').click({ force: true })
        cy.get('[class="form-control"]').invoke('val', event1)
        cy.wait(1000)
        cy.get("[type='submit']").click()
        cy.wait(2000)
      })
          //upload lvc "real" event that we want to trigger on
      cy.fixture('HESS_test_event_real_promising.txt').then((event1) => {
        cy.get('[data-testid="nav-testing"]').click({ force: true })
        cy.get('[class="form-control"]').invoke('val', event1)
        cy.wait(1000)
        cy.get("[type='submit']").click()
        cy.wait(2000)
      })
      //upload lvc "real" event that we want to trigger on
      cy.fixture('SWIFT_2018_03_25.txt').then((event1) => {
        cy.get('[data-testid="nav-testing"]').click({ force: true })
        cy.get('[class="form-control"]').invoke('val', event1)
        cy.wait(1000)
        cy.get("[type='submit']").click()
        cy.wait(2000)
      })
    })
  })