//./manage.py loaddata trigger_app/test_yamls/mwa_fs_proposal_settings.yaml

describe.skip('webpage loads and connects to the broker', () => {
  it('passes', () => {
    cy.visit('/')
    cy.get('.PositiveTransaction').exists
  })
})

describe.skip(`LVC events are grouped by id with source type, event type, Classification-Terrestrial, 
          Properties-HasNS, HasMassGap, Observation-Time, highest_probability_density_sky_location, 
          highest_probability_density_gw`, () => {
  it('upload lvc test event', () => {
    const graceDBId = "MS553322ab"

    cy.login()
    cy.visit('/')
    cy.wait(1000)

    // //upload lvc test event
    cy.fixture('LVC_example_early_warning_test.txt').then((event1) => {
      cy.get('[data-testid="nav-testing"]').click({ force: true })
      cy.get('[class="form-control"]').invoke('val', (event1.replaceAll("MS181101ab", graceDBId)))
      cy.get("[type='submit']").click()
    })
    //upload lvc test event
    cy.fixture('LVC_example_initial_test.txt').then((event1) => {
      cy.get('[data-testid="nav-testing"]').click({ force: true })
      cy.get('[class="form-control"]').invoke('val', (event1.replaceAll("MS181101ab", graceDBId)))
      cy.get("[type='submit']").click()
    })
    //events are grouped
    cy.get('.btn').click()
    cy.wait(1000)
    cy.contains(graceDBId).parent('tr').within(() => {
      cy.get('td > a').eq(0).click()
    })
    cy.get('[data-testid="eventgroup"]').find('tr').should('have.length', 3)
    cy.get('[data-testid="eventgroup"]').find('tr').eq(1)
      .within(() => {
        // all searches are automatically rooted to the found tr element
        cy.get('td').eq(1).contains('GW')
        cy.get('td').eq(2).contains('LVC')
        cy.get('td').eq(3).contains('Initial')
        cy.get('td').eq(4).contains('2018-11-01 22:22:46')
        cy.get('td').eq(6).contains(graceDBId)
      })
    cy.wait(10000)
  })
})

describe.skip('User can create proposal for MWA observations using LVC events', () => {
  it('create and view proposal', () => { 

    const proposalId = "testMWALVC"
    const proposalDescription = "This proposal tests MWA observation LVC triggers"

    cy.login()
    cy.visit('/')
    cy.wait(1000)
    
    cy.get("[data-testid='nav-proposal-settings']").click()
    cy.get("[data-testid='drop-create-proposal']").click()
    cy.get("#id_proposal_id").type(proposalId)
    cy.get("#proposal_description").type(proposalDescription)
    cy.get("#id_source_type").select('GW')
    cy.get("#event_telescope").select('LVC')
    cy.get("#id_event_any_duration").check()

    cy.get("#id_telescope").select('MWA_VCS')
    cy.get("#id_project_id").select('T001')
    cy.get("#id_testing").check()
    cy.get("[type='submit']").click()
    cy.wait(1000)

    cy.contains(proposalDescription)

  })
})

describe.skip('LVC events that don\'t trigger the proposal show as ignored', () => {
  it('passes', () => {
    it('upload lvc test event', () => { 
      const graceDBId = "MS11111s"

      cy.login()
      cy.visit('/')
      cy.wait(1000)
  
      //upload lvc test event
      cy.fixture('LVC_example_early_warning_real.txt').then((event1) => {
        cy.get('[data-testid="nav-testing"]').click({ force: true })
        cy.get('[class="form-control"]').invoke('val', (event1.replaceAll("MS181101ab", graceDBId)))
        cy.wait(1000)
        cy.get("[type='submit']").click()
        cy.wait(2000)
      })
    })
    it('proposal result shows event ignored', () => { })
  })
})

describe('LVC events that trigger the proposal show as observed', () => {
  it('upload lvc test event', () => { })
  it('proposal result triggers observation', () => { })
  it('send observation request to MWA', () => { })
  it('send alert data to Twilio', () => { })
})