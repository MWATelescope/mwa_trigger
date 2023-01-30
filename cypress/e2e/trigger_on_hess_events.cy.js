
describe('Test can do observations off HESS events', () => {
    it('create HESS trigger proposal', () => {

        const proposalId = "testMWAHESS"
        const proposalDescription = "This proposal tests MWA observation HESS triggers"

        cy.login()
        cy.visit('/')
        cy.wait(1000)

        cy.get("[data-testid='nav-proposal-settings']").click()
        cy.get("[data-testid='drop-create-proposal']").click()
        cy.get("#id_proposal_id").type(proposalId)
        cy.get("#proposal_description").type(proposalDescription)
        cy.get("#id_source_type").select('GRB')
        cy.get("#event_telescope").select('HESS')

        // Source options
        cy.get("#id_event_any_duration").click()

        cy.get("#id_telescope").select('MWA_VCS')
        cy.get("#id_project_id").select('T001')
        cy.get("#id_testing").check()
        cy.get("[type='submit']").click()
        cy.wait(1000)

        cy.contains(proposalDescription)
    })
})

describe('Early warning LVC events that trigger the proposal show decision outcome', () => {
    it('upload HESS real event and trigger an MWA observation with twilio notifications', () => {
        cy.login()
        cy.visit('/')
        cy.wait(1000)

        //upload lvc "real" event that we want to trigger on
        cy.fixture('HESS_test_event_real_promising.txt').then((event1) => {
            cy.get('[data-testid="nav-testing"]').click({ force: true })
            cy.get('[class="form-control"]').invoke('val', event1)
            cy.wait(1000)
            cy.get("[type='submit']").click()
            cy.wait(2000)
        })
        //proposal result shows event triggered
        cy.contains("HESS").parent('tr').within(() => {
            cy.get('td').eq(5).contains('GRB')
            cy.get('td').eq(7).contains('Triggered')
        })
        cy.get("[data-testid='nav-logs']").click()
        cy.get("[data-testid='drop-logs-proposals']").click()
        cy.contains("Above horizon so attempting to observer with MWA_VCS.")
        cy.wait(5000)

    })
})