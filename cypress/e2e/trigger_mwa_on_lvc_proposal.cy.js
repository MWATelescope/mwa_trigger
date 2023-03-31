//./manage.py loaddata trigger_app/test_yamls/mwa_fs_proposal_settings.yaml

describe("webpage loads", () => {
	it("passes", () => {
		cy.visit("/")
	})
})

describe(`LVC events are grouped by id with source type, event type, Classification-Terrestrial, 
          Properties-HasNS, HasMassGap, Observation-Time, highest_probability_density_sky_location, 
          highest_probability_density_gw`, () => {
	it("upload lvc test event", () => {
		const graceDBId = "MS553322ab"

		cy.login()
		cy.visit("/")

		// //upload lvc test event
		cy.fixture("LVC_early_warning_test_event.txt").then((event1) => {
			cy.get('[data-testid="nav-testing"]').click({ force: true })
			cy.get('[class="form-control"]').invoke(
				"val",
				event1.replaceAll("MS181101ab", graceDBId)
			)
			cy.get("[type='submit']").click()
		})
		//upload lvc test event
		cy.fixture("LVC_initial_test_event.txt").then((event1) => {
			cy.get('[data-testid="nav-testing"]').click({ force: true })
			cy.get('[class="form-control"]').invoke(
				"val",
				event1.replaceAll("MS181101ab", graceDBId)
			)
			cy.get("[type='submit']").click()
		})
		//events are grouped
		cy.visit("/event_group_log/?ignored=unknown&source_type=&telescope=")
		cy.contains(graceDBId)
			.parent("tr")
			.within(() => {
				cy.get("td > a").eq(0).click()
			})
		cy.get('[data-testid="eventgroup"]').find("tr").should("have.length", 3)
		cy.get('[data-testid="eventgroup"]')
			.find("tr")
			.eq(1)
			.within(() => {
				// all searches are automatically rooted to the found tr element
				cy.get("td").eq(1).contains("GW")
				cy.get("td").eq(2).contains("LVC")
				cy.get("td").eq(3).contains("Initial")
				cy.get("td").eq(4).contains("2018-11-01 22:22:46")
				cy.get("td").eq(6).contains(graceDBId)
			})
	})
})

describe("User can create proposal for MWA observations using LVC events", () => {
	it("create and view proposal", () => {
		const proposalId = "testMWALVC"
		const proposalDescription =
			"This proposal tests MWA observation LVC triggers"

		cy.login()
		cy.visit("/")

		cy.get("[data-testid='nav-proposal-settings']").click()
		cy.get("[data-testid='drop-create-proposal']").click()
		cy.get("#id_proposal_id").type(proposalId)
		cy.get("#proposal_description").type(proposalDescription)
		cy.get("#id_source_type").select("GW")
		cy.get("#event_telescope").select("LVC")

		cy.get("#id_telescope").select("MWA_VCS")
		cy.get("#id_project_id").select("T001")
		cy.get("#id_testing").check()
		cy.get("[type='submit']").click()

		cy.contains(proposalDescription)
	})
})

describe("Early warning LVC events that don't trigger the proposal show as ignored", () => {
	it("upload lvc early warning real event and get ignored because terrestial is > 95", () => {
		const graceDBId = "MS43555s"

		cy.login()
		cy.visit("/")

		//upload lvc "real" event that we don't want to trigger on because terrestial > 95
		cy.fixture("LVC_early_warning_ignore_observation_event.txt").then(
			(event1) => {
				cy.get('[data-testid="nav-testing"]').click({ force: true })
				cy.get('[class="form-control"]').invoke(
					"val",
					event1.replaceAll("MS181101ab", graceDBId)
				)
				cy.get("[type='submit']").click()
			}
		)
		//proposal result shows event ignored
		cy.visit("/event_group_log/?ignored=unknown&source_type=&telescope=")
		cy.contains(graceDBId)
			.parent("tr")
			.within(() => {
				cy.get("td").eq(8).contains("Ignored")
			})

		cy.get("[data-testid='nav-logs']").click()
		cy.get("[data-testid='drop-logs-proposals']").click()
		cy.contains(
			"The PROB_Terre probability (0.96) is greater than 0.95 so not triggering."
		)
	})
})

describe("Early warning LVC events that trigger the proposal show decision outcome", () => {
	it("upload lvc early warning real event and trigger an MWA observation with twilio notifications", () => {
		const graceDBId = "MS33841s"

		cy.login()
		cy.visit("/")

		//upload lvc "real" event that we want to trigger on
		cy.fixture("LVC_early_warning_promising_observation_event.txt").then(
			(event1) => {
				cy.get('[data-testid="nav-testing"]').click({ force: true })
				cy.get('[class="form-control"]').invoke(
					"val",
					event1.replaceAll("MS181101ab", graceDBId)
				)
				cy.get("[type='submit']").click()
			}
		)
		//proposal result shows event triggered
		cy.visit("/event_group_log/?ignored=unknown&source_type=&telescope=")
		cy.contains(graceDBId)
			.parent("tr")
			.within(() => {
				cy.get("td").eq(8).contains("Triggered")
			})
		cy.get("[data-testid='nav-logs']").click()
		cy.get("[data-testid='drop-logs-proposals']").click()
		cy.contains("Above horizon so attempting to observe with MWA_VCS.")
	})
})
