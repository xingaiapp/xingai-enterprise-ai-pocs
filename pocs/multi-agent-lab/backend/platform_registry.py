"""Agent registry for enterprise platform demo."""

AGENT_REGISTRY = [
    {
        "name": "Orchestrator Agent",
        "role": "Enterprise Brain",
        "goal": "Plan, route, and aggregate specialist agent work",
        "phase": 1,
        "status": "active",
    },
    {
        "name": "Research Agent",
        "role": "Technology Research Analyst",
        "goal": "Discover emerging opportunities",
        "tools": ["fake_research_tool", "cache_tool"],
        "phase": 1,
        "status": "active",
    },
    {
        "name": "Product Agent",
        "role": "Product Strategist",
        "goal": "Turn insights into product concepts and MVP features",
        "phase": 1,
        "status": "active",
    },
    {
        "name": "Tech Agent",
        "role": "Architecture Agent",
        "goal": "Design technical architecture for MVP",
        "phase": 1,
        "status": "active",
    },
    {
        "name": "Critic Agent",
        "role": "Risk Reviewer",
        "goal": "Review risks and propose mitigations",
        "phase": 1,
        "status": "active",
    },
    {
        "name": "Security Agent",
        "role": "Security Analyst",
        "goal": "Review security posture",
        "phase": 2,
        "status": "planned",
    },
    {
        "name": "Compliance Agent",
        "role": "Compliance Officer",
        "goal": "Policy and regulatory checks",
        "phase": 2,
        "status": "planned",
    },
    {
        "name": "Data Agent",
        "role": "Data Engineer",
        "goal": "Data pipeline and quality",
        "phase": 2,
        "status": "planned",
    },
    {
        "name": "Support Agent",
        "role": "Support Specialist",
        "goal": "Incident triage and customer support",
        "phase": 3,
        "status": "planned",
    },
    {
        "name": "Finance Agent",
        "role": "Financial Analyst",
        "goal": "Cost and ROI analysis",
        "phase": 3,
        "status": "planned",
    },
    {
        "name": "HR Agent",
        "role": "People Operations",
        "goal": "Workforce and org planning",
        "phase": 3,
        "status": "planned",
    },
]

MCP_REGISTRY = [
    {"name": "Research Web MCP", "target": "Web / Knowledge", "phase": 2, "status": "planned"},
    {"name": "GitHub MCP", "target": "GitHub", "phase": 2, "status": "planned"},
    {"name": "Jira MCP", "target": "Jira", "phase": 2, "status": "planned"},
    {"name": "ServiceNow MCP", "target": "ServiceNow", "phase": 3, "status": "planned"},
    {"name": "SharePoint MCP", "target": "SharePoint", "phase": 3, "status": "planned"},
    {"name": "SAP MCP", "target": "SAP", "phase": 3, "status": "planned"},
]
