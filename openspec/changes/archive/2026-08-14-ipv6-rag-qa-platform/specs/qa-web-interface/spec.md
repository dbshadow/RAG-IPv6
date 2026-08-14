## ADDED Requirements

### Requirement: Interactive Chat Interface
The web interface SHALL provide a clean, modern conversational UI allowing users to ask questions regarding IPv6 specifications and receive answers.

#### Scenario: User submits question
- **WHEN** user types an IPv6 question and clicks send or presses Enter
- **THEN** the message is appended to the chat stream and an answering indicator appears

### Requirement: Real-Time Streaming and Markdown Rendering
The web interface SHALL render incoming tokens in real-time as markdown formatted text (including code blocks, bullet points, and headings).

#### Scenario: Real-time token display
- **WHEN** streaming chunks are received from the backend
- **THEN** the chat bubble updates dynamically with formatted markdown

### Requirement: Interactive Citation Inspector
The web interface SHALL display citation tags/chips for each RFC referenced in the answer, allowing users to click or hover to view the referenced RFC section, text snippet, and link to IETF datatracker.

#### Scenario: Inspect RFC reference
- **WHEN** user clicks on an RFC citation badge (e.g. `RFC 8200 Section 3`)
- **THEN** a detail card/drawer expands showing the exact excerpt and a direct link to the RFC document
