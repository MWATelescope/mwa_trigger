
describe('Test HESS events will group with swift', () => {
    it('create HESS and swift events, check that they group', () => {

        cy.login()
        cy.visit('/')
        cy.wait(1000)

        const swiftId = "144329"
        // //upload lvc test event
        cy.fixture('HESS_test_event_test_promising.txt').then((event1) => {
            cy.get('[data-testid="nav-testing"]').click({ force: true })
            cy.get('[class="form-control"]').invoke('val', (event1.replaceAll("1102329", swiftId)))
            cy.get("[type='submit']").click()
        })
        //upload lvc test event
        cy.fixture('SWIFT_2018_03_25.txt').then((event1) => {
            cy.get('[data-testid="nav-testing"]').click({ force: true })
            cy.get('[class="form-control"]').invoke('val', (event1.replaceAll("817564", swiftId)))
            cy.get("[type='submit']").click()
        })
        // events are grouped
        cy.get('.btn').click()
        cy.wait(1000)
        cy.contains(swiftId).parent('tr').within(() => {
            cy.get('td > a').eq(0).click()
        })
        cy.get('[data-testid="eventgroup"]').find('tr').should('have.length', 3)
        cy.get('[data-testid="eventgroup"]').find('tr').eq(1)
            .within(() => {
                // all searches are automatically rooted to the found tr element
                cy.get('td').eq(1).contains('GRB')
                cy.get('td').eq(6).contains(swiftId)
            })
    })

})


describe('Test can create proposals to do observations off HESS events', () => {
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

describe.only('HESS events that trigger the proposal show decision outcome', () => {
    it('upload HESS real event and trigger an MWA observation with twilio notifications', () => {
        cy.login()
        cy.visit('/')
        cy.wait(1000)

        const hessId = '222222'

        //upload lvc "real" event that we want to trigger on
        cy.fixture('HESS_test_event_real_promising.txt').then((event1) => {
            cy.get('[data-testid="nav-testing"]').click({ force: true })
            cy.get('[class="form-control"]').invoke('val', (event1.replaceAll("1102329", hessId)))
            cy.wait(1000)
            cy.get("[type='submit']").click()
            cy.wait(2000)
        })
        //proposal result shows event triggered
        cy.contains(hessId).parent('tr').within(() => {
            cy.get('td').eq(4).contains('GRB')
            cy.get('td').eq(2).contains('HESS')
        })
        cy.get("[data-testid='nav-logs']").click()
        cy.get("[data-testid='drop-logs-proposals']").click()
        cy.get(".fl-table > tbody:nth-child(2) > tr:nth-child(1)").within(() => {
            cy.get('td').eq(6).contains('HESS rate significance is')
            cy.get('td').eq(6).contains('Above horizon so attempting to observe')
        })
    })
})