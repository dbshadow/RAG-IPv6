## ADDED Requirements

### Requirement: Dark and Light Theme Switching
The web interface SHALL provide a theme toggle mechanism enabling users to switch between a Dark theme (dark gray background) and a Light theme (pure white background).

#### Scenario: Switch from Dark to Light theme
- **WHEN** user clicks the "Light" mode button
- **THEN** the interface background immediately updates to white with light theme styling and the preference is saved to localStorage

#### Scenario: Switch from Light to Dark theme
- **WHEN** user clicks the "Dark" mode button
- **THEN** the interface background immediately updates to dark gray with dark theme styling and the preference is saved to localStorage

#### Scenario: Theme persistence across page reloads
- **WHEN** user reloads or revisits the web application
- **THEN** the application initializes with the previously saved theme from localStorage
