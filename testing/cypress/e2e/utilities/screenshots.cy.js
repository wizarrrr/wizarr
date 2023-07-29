// cypress spec that will go to every page and take a screenshot

// list of pages already visited
const folder = '../automated'
let visited = []

const takeScreenshot = (name, path, cy) => {
    cy.visit('http://127.0.0.1:9999/' + path).then((win) => {
        win.eval('window.utils.theme.setDark()');
        cy.screenshot(`${folder}/${name}-dark`);
    });
    cy.visit('http://127.0.0.1:9999/' + path).then((win) => {
        win.eval('window.utils.theme.setLight()');
        cy.screenshot(`${folder}/${name}-light`);
    });
}

describe('Screenshots', () => {
    it('takes screenshots of all pages', () => {

        cy.viewport(window.screen.width, window.screen.height);

        cy.exec(`ls ./cypress/screenshots`).then((result) => {
            if (result.stdout.includes('automated')) {
                cy.exec(`rm -rf ./cypress/screenshots/automated`)
            }
        })

        cy.exec('ls ../').then((ls_result) => {
            if (ls_result.stdout.includes('manage.py')) {
                cy.log('manage.py found, creating new user')
                cy.exec('python3 ../manage.py create_user --username cypress --password cypress --email cypress@testing.com', { failOnNonZeroExit: false }).then((manage_result) => {
                    cy.log(manage_result.stdout)
                })
            }
        })

        cy.visit('http://127.0.0.1:9999/login')
        cy.get('#username').type('cypress')
        cy.get('#password').type('cypress')
        cy.get('button[type="submit"]').click()

        cy.wait(500)

        // list of pages to visit
        const pages = [
            {
                name: 'homepage',
                path: ''
            },
            {
                name: 'admin/invite',
                path: 'admin/invite'
            },
            {
                name: 'admin/invites',
                path: 'admin/invites'
            },
            {
                name: 'admin/users',
                path: 'admin/users'
            },
            {
                name: 'admin/settings/main',
                path: 'admin/settings'
            },
            {
                name: 'admin/settings/general',
                path: 'admin/settings/general'
            },
            {
                name: 'admin/settings/requests',
                path: 'admin/settings/requests'
            },
            {
                name: 'admin/settings/api',
                path: 'admin/settings/api'
            },
            {
                name: 'admin/settings/notifications',
                path: 'admin/settings/notifications'
            },
            {
                name: 'admin/settings/discord',
                path: 'admin/settings/discord'
            },
            {
                name: 'admin/settings/html',
                path: 'admin/settings/html'
            }
        ]

        pages.forEach((page) => {
            takeScreenshot(page.name, page.path, cy)
        })

        cy.exec('ls ../').then((ls_result) => {
            if (ls_result.stdout.includes('manage.py')) {
                cy.log('manage.py found, creating new user')
                cy.exec('python3 ../manage.py delete_user --username cypress --y true', { failOnNonZeroExit: false }).then((manage_result) => {
                    cy.log(manage_result.stdout)
                })
            }
        })

        // takeScreenshot('home', '', cy)
    })
})