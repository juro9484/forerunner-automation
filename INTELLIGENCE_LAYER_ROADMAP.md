# Intelligence Layer Roadmap

**Status:** Planning Phase
**Priority:** Build after 3-5 clients onboarded
**Purpose:** Add AI-powered insights and analytics to increase product value

---

## What is the Intelligence Layer?

An AI system that analyzes historical email/claim data to provide:

### For Public Adjusters (PAs):
- **Claim insights** - "This type of claim usually takes 45 days to close"
- **Pattern detection** - "80% of water damage claims need contractor follow-up"
- **Predictive analytics** - "This claim is likely to need supplemental estimate"
- **Adjuster performance** - "Average response time: 2.3 days"
- **Client communication** - Auto-suggest responses based on past similar claims

### For Roak Systems (You):
- **Product differentiation** - Harder to replace than "just automation"
- **Higher pricing** - Intelligence = premium tier ($200/mo vs $50/mo)
- **Stickiness** - More data over time = better insights = harder to switch
- **Upsell opportunities** - Basic automation → Intelligence add-on

---

## Why Store Extra Data NOW?

**Problem:** If we don't store raw email content now, we can't build intelligence later without re-processing.

**Solution:** Store extra fields in SQLite now (minimal cost), backfill intelligence later.

### Current Database Schema (Missing Data):
```sql
CREATE TABLE processed_emails (
    email_id TEXT PRIMARY KEY,
    claim_number TEXT,
    sender TEXT,
    subject TEXT,
    received_timestamp TEXT,
    processed_timestamp TEXT,
    status TEXT,
    error_message TEXT
);
```

**What's missing for intelligence:**
- ❌ Raw email body (can't re-analyze later)
- ❌ AI summary/response (can't see what AI said)
- ❌ Email type (contract vs regular)
- ❌ Attachments metadata (can't analyze document patterns)

### Proposed Enhanced Schema:
```sql
CREATE TABLE processed_emails (
    -- Existing fields
    email_id TEXT PRIMARY KEY,
    claim_number TEXT,
    sender TEXT,
    subject TEXT,
    received_timestamp TEXT,
    processed_timestamp TEXT,
    status TEXT,
    error_message TEXT,

    -- NEW: Intelligence fields
    email_body_text TEXT,              -- Raw plain text content
    email_body_html TEXT,              -- Raw HTML content
    email_type TEXT,                   -- 'contract', 'regular', 'follow_up'
    ai_summary_title TEXT,             -- AI-generated title
    ai_summary_description TEXT,       -- AI-generated description
    ai_model_used TEXT,                -- Which model (for A/B testing)
    note_posted_to_claim TEXT,         -- URL/reference to CRM note
    sentiment TEXT,                    -- 'positive', 'neutral', 'negative', 'urgent'
    priority_score INTEGER,            -- 1-10 urgency score

    -- Metadata for analytics
    processing_duration_ms INTEGER,    -- How long did it take?
    tokens_used INTEGER,               -- AI API cost tracking
    has_attachments BOOLEAN,
    attachment_count INTEGER
);

-- New table for claim lifecycle tracking
CREATE TABLE claim_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_number TEXT NOT NULL,
    event_type TEXT NOT NULL,          -- 'email_received', 'note_posted', 'status_change'
    event_timestamp TEXT NOT NULL,
    event_data JSON,                   -- Flexible data storage
    created_at TEXT NOT NULL
);

-- New table for AI embeddings (for semantic search)
CREATE TABLE email_embeddings (
    email_id TEXT PRIMARY KEY,
    embedding BLOB,                    -- Vector embedding from AI
    model_version TEXT,
    created_at TEXT,
    FOREIGN KEY (email_id) REFERENCES processed_emails(email_id)
);
```

---

## The Intelligence Pipeline

### Phase 1: Data Collection (NOW - Build This First)
1. **Update database schema** - Add intelligence fields
2. **Update main.py** - Save raw email body and AI responses
3. **Store everything** - Even if we don't use it yet
4. **Let it run** - Collect 30-90 days of data across multiple clients

**Cost:** ~Free (SQLite storage is cheap, <1MB per 1000 emails)

### Phase 2: Historical Ingestion (When Ready for Intelligence)
Build a pipeline to backfill old data:

```python
# Example: src/intelligence/ingest_pipeline.py

def ingest_historical_emails():
    """
    Backfill intelligence data for emails already processed.

    For each processed email (that's missing intelligence fields):
    1. Re-fetch email from IMAP (if still available)
    2. Re-run AI summarization
    3. Update database with intelligence fields
    4. Generate embeddings for semantic search
    """

    # Find emails missing intelligence data
    emails_to_backfill = db.query("""
        SELECT * FROM processed_emails
        WHERE email_body_text IS NULL
        AND received_timestamp > DATE('now', '-90 days')
    """)

    for email in emails_to_backfill:
        # Re-fetch from IMAP if available
        raw_email = fetch_email_by_id(email.email_id)

        # Re-run AI analysis
        summary = ai_summarize(raw_email.body)
        sentiment = ai_analyze_sentiment(raw_email.body)
        priority = ai_calculate_priority(raw_email)

        # Update database
        db.update(email.email_id, {
            'email_body_text': raw_email.body_text,
            'ai_summary_title': summary.title,
            'sentiment': sentiment,
            'priority_score': priority
        })
```

**When to build:** After 3-5 clients, 30+ days of data per client

### Phase 3: Intelligence Features (Revenue Generator)

#### Feature 1: Claim Timeline Intelligence
```
"Based on 247 similar water damage claims:
 - Average time to close: 42 days
 - 73% required contractor follow-up
 - Peak activity: Days 7-14 (adjuster inspections)"
```

**Implementation:**
- Aggregate claim_events by claim type
- Calculate statistics (avg duration, common patterns)
- Show in dashboard or email digest

#### Feature 2: Smart Search (Semantic)
```
PA searches: "claims where adjuster asked for more photos"

Instead of keyword search, AI understands intent:
- Finds claims with "need additional documentation"
- Finds "please provide supplemental images"
- Finds "inspection photos insufficient"
```

**Implementation:**
- Use Claude to generate embeddings for each email
- Store in `email_embeddings` table
- Search by semantic similarity (not keywords)

#### Feature 3: Predictive Insights
```
"This claim is 83% likely to need a supplement within 2 weeks"
"Recommended action: Schedule contractor site visit"
```

**Implementation:**
- Train model on historical patterns
- Feature extraction: claim type, adjuster, damage type, initial estimate
- Predict outcomes based on similar past claims

#### Feature 4: Auto-Response Suggestions
```
Adjuster emails: "Need proof of prior condition"

AI suggests response:
"Based on 15 similar requests, PAs usually send:
 - Pre-loss photos from homeowner
 - Property inspection report from purchase
 - Insurance policy declarations page"
```

**Implementation:**
- Analyze past email threads
- Extract successful response patterns
- Suggest templates based on context

---

## Technical Architecture

### Current (Automation Only):
```
Email Inbox → Monitor → AI Summary → Post to CRM
                ↓
            SQLite (basic tracking)
```

### Future (With Intelligence):
```
Email Inbox → Monitor → AI Summary → Post to CRM
                ↓           ↓
            SQLite      Extract Features
               ↓              ↓
          Analytics ← AI Intelligence Engine
               ↓              ↓
         Dashboard    Embeddings Store
               ↓              ↓
        Insights API ← Vector Search
```

### Components to Build:

1. **Enhanced Database Layer**
   - Migration script to add fields
   - Update EmailDatabase class to store raw content
   - Add claim_events tracking

2. **Intelligence Engine** (`src/intelligence/`)
   - `embeddings.py` - Generate/store email embeddings
   - `analytics.py` - Calculate statistics and patterns
   - `predictions.py` - ML models for predictions
   - `semantic_search.py` - Similarity search

3. **API Layer** (Optional - for dashboard)
   - FastAPI server exposing intelligence endpoints
   - `/api/claims/{id}/insights` - Get insights for a claim
   - `/api/search?q=...` - Semantic search
   - `/api/analytics/overview` - Aggregate stats

4. **Dashboard** (Optional - premium feature)
   - React/Next.js frontend
   - Charts showing claim patterns
   - Search interface
   - Insight cards

---

## Database Migration Strategy

### Step 1: Add Fields (Non-Breaking)
```bash
# Run migration script (doesn't affect existing data)
python3 src/migrate_database_v2.py
```

This adds new columns with NULL values - existing automation keeps working.

### Step 2: Update Code to Populate Fields
Update `main.py` and `email_database.py`:
```python
# Old
database.mark_processed(
    email_id=email_data.email_id,
    claim_number=email_data.claim_number,
    sender=email_data.sender,
    subject=email_data.subject
)

# New
database.mark_processed(
    email_id=email_data.email_id,
    claim_number=email_data.claim_number,
    sender=email_data.sender,
    subject=email_data.subject,
    # NEW FIELDS
    email_body_text=email_data.body,
    email_body_html=email_data.html_body,
    email_type='contract' if is_contract else 'regular',
    ai_summary_title=summary.title,
    ai_summary_description=summary.description,
    ai_model_used='claude-3-5-sonnet-20241022'
)
```

### Step 3: Let Data Accumulate
Run for 30-90 days collecting rich data across clients.

### Step 4: Backfill (Optional)
Re-fetch old emails from IMAP and populate missing fields.

### Step 5: Build Intelligence Layer
Once you have data, build the features!

---

## Migration to Postgres (Optional)

**When:** 20+ clients, millions of records, need advanced features

**Why SQLite is fine for now:**
- Handles 1M+ rows easily
- No server costs
- Zero configuration
- Perfect for <20 clients

**When to migrate to Postgres:**
- Multiple users querying simultaneously (dashboard)
- Need full-text search
- Want JSON field indexing
- Building real-time analytics dashboard
- Want to use Timescale for time-series

**Migration path:**
```python
# Export SQLite to Postgres
sqlite3 automation.db .dump | psql new_database
```

Or use a tool like `pgloader`:
```bash
pgloader automation.db postgresql://user:pass@host/db
```

All queries stay the same (both use SQL).

---

## Cost Estimates

### Current (Automation Only):
- Server: $25/mo (Google Cloud e2-medium)
- Claude API: $5-15/day depending on volume
- **Total: ~$175-500/mo** for automation

### With Intelligence Layer:
- Server: Same (SQLite handles it)
- Claude API: +$5-10/day for embeddings
- Postgres (optional): +$15/mo (if needed)
- **Total: ~$325-650/mo**

**Revenue impact:**
- Current pricing: $50/adjuster/mo = $500/mo for 10 adjusters
- With intelligence: $75-100/adjuster/mo = $750-1000/mo for 10 adjusters
- **ROI: +$250-500/mo revenue vs +$150/mo cost**

---

## Competitive Moat

### Without Intelligence (Easy to Compete):
- "We automate email processing for PAs"
- Competitor can build in 2-3 months
- Pricing pressure (race to bottom)

### With Intelligence (Hard to Compete):
- "We provide AI insights based on YOUR historical data"
- Competitor needs YOUR data (can't replicate)
- More data over time = better insights = stickier
- Switching cost: lose all historical intelligence

**Intelligence = Moat**

---

## Implementation Timeline

### Immediate (This Week):
- [ ] Add database migration script
- [ ] Update EmailDatabase to accept intelligence fields
- [ ] Update main.py to pass raw email body
- [ ] Deploy and start collecting data

**Time:** 2-3 hours
**Cost:** $0 (just schema changes)

### Short Term (Month 1-2):
- [ ] Let data accumulate across 3-5 clients
- [ ] Validate data quality (check DB periodically)
- [ ] Ensure all fields populated correctly

**Time:** Passive monitoring
**Cost:** Storage only (~1MB per 1000 emails)

### Medium Term (Month 3-4):
- [ ] Build basic analytics queries
- [ ] Create simple dashboard (optional)
- [ ] Build semantic search (embeddings)
- [ ] Calculate basic insights

**Time:** 1-2 weeks of development
**Cost:** +$5-10/day for embeddings

### Long Term (Month 6+):
- [ ] Predictive models
- [ ] Auto-response suggestions
- [ ] Multi-client benchmarking
- [ ] Premium intelligence tier

**Time:** Ongoing feature development
**Revenue:** Premium pricing tier

---

## Next Steps for Claude

When you're ready to build this, tell Claude:

> "Read INTELLIGENCE_LAYER_ROADMAP.md. We're ready to implement Phase 1 (Data Collection).
>
> Add the intelligence fields to the database schema and update the code to populate them.
>
> We have [X] clients now with [Y] days of data. Let's start collecting rich data for the intelligence layer."

Claude will:
1. Read this document for context
2. Create database migration script
3. Update EmailDatabase class
4. Update main.py to populate new fields
5. Test the migration
6. Deploy to server

Then just let it run and accumulate data!

---

## Questions to Answer Before Building

1. **How many clients do we have?** (Build after 3-5)
2. **How much data exists?** (Need 30+ days per client)
3. **What's the first intelligence feature users want?** (Ask Beau!)
4. **Premium tier or included?** (Pricing strategy)
5. **Dashboard needed?** (Or just email digest?)

**Ask your first client (Beau) what insights would help him most!**

---

## Resources

- Database migration guide: See `src/migrate_database_v2.py` (to be created)
- Claude embeddings: https://docs.anthropic.com/claude/docs/embeddings
- Semantic search tutorial: https://www.pinecone.io/learn/semantic-search/
- SQLite scaling: https://www.sqlite.org/whentouse.html

---

**Remember:** Start simple. Add fields now (cheap), build features later (when valuable).

The hard part isn't building the intelligence - it's having the data to train on. **Collect data NOW!**
