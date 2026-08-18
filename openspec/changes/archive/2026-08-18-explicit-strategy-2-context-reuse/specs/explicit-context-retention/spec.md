## ADDED Requirements

### Requirement: Explicit Strategy 2 Context Reuse
The `ConversationRouter` SHALL identify queries that request further elaboration or drill-down on information present in the conversation history without requiring new RFC database search.

#### Scenario: User asks to elaborate on a specific point from previous answer
- **WHEN** user sends "請詳細解釋第 2 點的內容" or "上面提到的 Hop Limit 是什麼意思？"
- **THEN** router returns `decision="REUSE_CONTEXT"` with zero retrieval latency and skips LLM query rewriting

#### Scenario: Frontend rendering of Context Reuse
- **WHEN** the SSE stream delivers a `router` event with `decision="REUSE_CONTEXT"`
- **THEN** the web interface renders a distinct badge `🔄 沿用上下文 (零檢索)`
