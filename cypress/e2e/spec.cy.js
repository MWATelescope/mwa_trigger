describe('webpage loads and connects to broker', () => {
  it('passes', () => {
    cy.visit('/')
    cy.get('.PositiveTransaction').exists
  })
})