# AI Automation Company - Project Context

## The Vision

We're building an AI automation company for small businesses. Lots of small companies are drowning in manual work - copying data between systems, monitoring emails, updating CRMs, tracking information. We use AI and automation to handle this work so they can focus on their actual business.

**Business model:** We help businesses identify what can be automated, build custom solutions for their specific workflows, and run everything as a managed service.

## Where We Are

We've built our first MVP for a client in the insurance claims space. The system monitors their email, uses AI to generate summaries, and automatically posts to their CRM. It's deployed, running in production, and working.

**Tech:** Python, browser automation (Playwright), AI (Claude API), deployed as Windows service

This proves the concept works. Now we need to figure out if this specific vertical has legs, or if we pivot to other types of businesses with similar manual work problems.

## Where We're Going

Build a real company:
- Perfect the solution for our first client
- Use them as a case study
- Get next few clients (same vertical or different - TBD)
- Build reusable components that work across different use cases
- Scale to sustainable recurring revenue
- Eventually build a team

Path: nail it with one client → prove we can repeat it → scale up.

## What We're Figuring Out

**Business questions:**
- Is insurance claims the right vertical or do we go broader?
- What's the pricing model that works?
- How do we find the next 5-10 clients?
- When do we need to hire?
- How do we make delivery repeatable without being too custom?

**Technical questions:**
- What automation patterns work across different clients?
- How do we handle different CRMs, email systems, workflows?
- What features unlock growth vs. just add complexity?
- How do we monitor and maintain systems at scale?

## Why This Could Work

**The market gap:**
- Small businesses have tons of manual work
- They can't afford enterprise automation solutions
- Most automation tools are either too simple (Zapier) or too complex (RPA platforms)
- AI changes the game - can handle judgment calls, not just simple triggers

**Our approach:**
- Custom solutions (not one-size-fits-all SaaS)
- Advisory + implementation + managed service (hybrid model)
- AI-native (using latest models, adapting as they improve)
- Fast iteration (weeks, not months)

**Target customers:**
- Small businesses with repetitive manual work
- Verticals where time = money (consultants, agencies, service businesses)
- Anyone spending hours copying data, monitoring systems, updating tools

## Current MVP

Four main components:
1. Email monitor - watches inbox, extracts relevant data
2. AI processor - uses Claude to interpret and format information
3. System integrator - posts to external systems (CRM, database, etc.)
4. Orchestrator - runs 24/7, handles errors, logs everything

It's modular. We can swap out the email monitor for a different data source, or the CRM integration for a different system, depending on the client.

## How to Think About This Project

**For technical work:**
- Stability first (production code for paying clients)
- Build for reusability (can this work for other clients?)
- Document patterns (we're learning as we go)

**For business decisions:**
- Does this help us scale or just add complexity?
- Is this vertical-specific or broadly useful?
- Can we sell this to other clients?

**Current phase:**
- Week 2 of production with first client
- Monitoring, bug fixes, stability
- Learning what works and what doesn't
- Co-founder handling legal/company setup, contracts, go-to-market strategy

## What You (Claude) Should Know

When helping with this project:
- We're building a company, not just a script
- Think about scalability and reusability
- Ask about business impact when it matters
- Flag risks clearly
- Suggest improvements based on patterns you see

The insurance claims client is our first one, but the vision is bigger - any small business with manual work that AI can handle.

---

**The mission:** Help small businesses eliminate manual work using AI. Start with one vertical, prove it works, scale from there.
