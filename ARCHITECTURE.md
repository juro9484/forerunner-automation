# Forerunner Automation Platform Architecture

## Design Principles

1. **Adapters are swappable** - Email and CRM providers can be changed via config
2. **Modules are composable** - Features can be enabled/disabled per client
3. **One codebase** - All clients run the same code with different configs
4. **Plugin architecture** - Easy to add new adapters and modules

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT CONFIG                          │
│  (Which adapters and modules to use for this client)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CORE ORCHESTRATOR                         │
│  (main.py - loads adapters and modules based on config)     │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
         ┌──────────┐  ┌──────────┐  ┌──────────┐
         │  EMAIL   │  │   CRM    │  │ MODULES  │
         │ ADAPTER  │  │ ADAPTER  │  │ (Plugins)│
         └──────────┘  └──────────┘  └──────────┘
              │             │              │
         ┌────┴────┐   ┌────┴────┐   ┌────┴────────────┐
         │ Outlook │   │  Claim  │   │ CommentAddition │
         │  Gmail  │   │  Titan  │   │ AttachmentUpload│
         │ Office  │   │Xactimate│   │ ContractParsing │
         └─────────┘   └─────────┘   │  RiskScoring    │
                                     │ IdleClaimAlerts │
                                     └─────────────────┘
```

## Layer 1: Adapters

### Email Adapters
Connect to email providers and fetch emails.

**Interface:**
- `connect()` - Establish connection
- `fetch_emails()` - Get unread emails
- `mark_as_read(email_id)` - Mark email as processed
- `disconnect()` - Clean up

**Implementations:**
- `OutlookAdapter` - Office365 with OAuth
- `GmailAdapter` - Gmail with app password or OAuth
- `Office365Adapter` - Office365 with modern auth

### CRM Adapters
Connect to CRM systems and perform actions.

**Interface:**
- `connect()` - Login to CRM
- `search_claim(claim_number)` - Find claim
- `post_note(claim_number, title, description)` - Add note/comment
- `upload_attachment(claim_number, file_path, folder)` - Upload file
- `create_claim(client_data)` - Create new claim
- `get_claim_state(claim_number)` - Get claim details
- `disconnect()` - Logout

**Implementations:**
- `ClaimTitanAdapter` - Claim Titan CRM
- `XactimateAdapter` - Xactimate system
- `ServiceBenchAdapter` - ServiceBench platform

## Layer 2: Automation Modules

### What Are Modules?
Reusable automation logic that works across different CRMs.

Each module:
- Is enabled/disabled via client config
- Uses CRM adapter methods (CRM-agnostic)
- Has its own configuration options

### Module: CommentAddition

**Purpose:** Summarize emails and post to CRM

**Dependencies:**
- Email adapter (any)
- CRM adapter (must support `post_note()`)
- AI summarizer

**Config:**
```python
MODULES = ["CommentAddition"]
COMMENT_ADDITION_ENABLED = true
```

**Logic:**
```python
1. Email arrives
2. Summarize with AI
3. Call crm_adapter.post_note(claim_number, title, description)
4. CRM adapter handles Claim Titan vs Xactimate differences
```

### Module: AttachmentUpload

**Purpose:** Download email attachments and upload to CRM

**Dependencies:**
- Email adapter (any)
- CRM adapter (must support `upload_attachment()`)
- AI for folder categorization

**Config:**
```python
MODULES = ["AttachmentUpload"]
ATTACHMENT_UPLOAD_ENABLED = true
ATTACHMENT_AI_CATEGORIZATION = true
```

**Logic:**
```python
1. Email has attachments
2. Download attachments
3. Use AI to categorize (invoice, photo, estimate, etc.)
4. Call crm_adapter.upload_attachment(claim, file, folder)
5. CRM adapter handles upload for specific CRM
```

### Module: ContractParsing

**Purpose:** Parse new client contracts and create claims

**Dependencies:**
- Email adapter (any)
- CRM adapter (must support `create_claim()`)
- AI vision for PDF parsing

**Config:**
```python
MODULES = ["ContractParsing"]
CONTRACT_PARSING_ENABLED = true
CONTRACT_KEYWORDS = ["contract", "agreement"]
```

**Logic:**
```python
1. Email with "contract" in subject
2. Extract PDF attachment
3. Use AI vision to extract client data
4. Call crm_adapter.create_claim(client_data)
5. CRM adapter handles claim creation for specific CRM
```

### Module: RiskScoring

**Purpose:** Track claim events and score risk

**Dependencies:**
- Event database
- AI for event extraction

**Config:**
```python
MODULES = ["RiskScoring"]
RISK_SCORING_ENABLED = true
RISK_ALERT_THRESHOLD = 7
```

**Logic:**
```python
1. Email processed
2. Extract event data (carrier_response, payment_notice, etc.)
3. Update claim state in database
4. Calculate risk score
5. Alert if score > threshold
```

### Module: IdleClaimAlerts

**Purpose:** Alert when claims haven't been updated

**Dependencies:**
- Event database
- Notification system (email/SMS)

**Config:**
```python
MODULES = ["IdleClaimAlerts"]
IDLE_CLAIM_THRESHOLD_DAYS = 14
ALERT_EMAIL = "admin@pa.com"
```

**Logic:**
```python
1. Daily cron job
2. Query claims with no activity > 14 days
3. Generate alert list
4. Send email to PA admin
```

## Layer 3: Client Configuration

### Config File Structure

Each client has a `.env` file:

```bash
# Client Identity
CLIENT_ID=forerunner_claims
CLIENT_NAME="Forerunner Claims"

# Email Adapter Selection
EMAIL_ADAPTER=outlook
BOT_EMAIL_USER=support@forerunnerclaims.com
USE_OAUTH=true
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
AZURE_TENANT_ID=...

# CRM Adapter Selection
CRM_ADAPTER=claim_titan
CLAIM_TITAN_USER=beau@forerunnerclaims.com
CLAIM_TITAN_PASS=...
CLAIM_TITAN_URL=https://claimtitan.com/welcome

# Module Configuration
ENABLED_MODULES=CommentAddition,AttachmentUpload,ContractParsing

# Module-Specific Settings
COMMENT_ADDITION_ENABLED=true

ATTACHMENT_UPLOAD_ENABLED=true
ATTACHMENT_AI_CATEGORIZATION=true

CONTRACT_PARSING_ENABLED=true
CONTRACT_KEYWORDS=contract,agreement

RISK_SCORING_ENABLED=false
IDLE_CLAIM_ALERTS_ENABLED=false

# AI Configuration
ANTHROPIC_API_KEY=...
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# System Configuration
BROWSER_POOL_SIZE=3
MAX_ADJUSTERS_PER_SERVER=40
BROWSER_HEADLESS=true
LOG_LEVEL=INFO
```

## Code Structure

```
src/
├── main.py                          # Core orchestrator
├── config.py                        # Configuration loader
├── summarizer.py                    # AI summarization (shared)
│
├── adapters/
│   ├── __init__.py
│   ├── base_adapter.py             # Base classes/interfaces
│   │
│   ├── email/
│   │   ├── __init__.py
│   │   ├── base.py                 # EmailAdapter interface
│   │   ├── outlook.py              # OutlookAdapter
│   │   ├── gmail.py                # GmailAdapter (future)
│   │   └── office365.py            # Office365Adapter (future)
│   │
│   └── crm/
│       ├── __init__.py
│       ├── base.py                 # CRMAdapter interface
│       ├── claim_titan.py          # ClaimTitanAdapter
│       ├── xactimate.py            # XactimateAdapter (future)
│       └── servicebench.py         # ServiceBenchAdapter (future)
│
├── modules/
│   ├── __init__.py
│   ├── base_module.py              # AutomationModule interface
│   ├── comment_addition.py         # CommentAdditionModule
│   ├── attachment_upload.py        # AttachmentUploadModule
│   ├── contract_parsing.py         # ContractParsingModule
│   ├── risk_scoring.py             # RiskScoringModule (future)
│   └── idle_claim_alerts.py        # IdleClaimAlertsModule (future)
│
├── database/
│   ├── __init__.py
│   ├── models.py                   # SQLAlchemy models
│   └── factory.py                  # Database factory
│
└── utils/
    ├── __init__.py
    ├── browser_pool.py             # Browser pool for parallel processing
    ├── logger.py                   # Logging utilities
    └── exceptions.py               # Custom exceptions
```

## Example: How It All Works Together

### Client Config:
```bash
EMAIL_ADAPTER=outlook
CRM_ADAPTER=claim_titan
ENABLED_MODULES=CommentAddition,AttachmentUpload
```

### main.py Orchestration:
```python
# 1. Load configuration
config = Config()

# 2. Initialize adapters (based on config)
email_adapter = AdapterFactory.create_email_adapter(
    adapter_type=config.EMAIL_ADAPTER,
    config=config
)

crm_adapter = AdapterFactory.create_crm_adapter(
    adapter_type=config.CRM_ADAPTER,
    config=config
)

# 3. Load enabled modules (based on config)
modules = ModuleLoader.load_modules(
    enabled_modules=config.ENABLED_MODULES,
    email_adapter=email_adapter,
    crm_adapter=crm_adapter,
    config=config
)

# 4. Process emails
with email_adapter:
    emails = email_adapter.fetch_emails()

    for email_data in emails:
        # Each module processes the email
        for module in modules:
            if module.should_process(email_data):
                module.process(email_data)

        # Mark as processed
        email_adapter.mark_as_read(email_data.email_id)
```

### What Happens:
1. Email arrives for Claim #12345
2. **CommentAddition** module runs:
   - Summarizes email
   - Calls `crm_adapter.post_note()` (CRM adapter handles Claim Titan specifics)
3. **AttachmentUpload** module runs:
   - Downloads attachments
   - Categorizes with AI
   - Calls `crm_adapter.upload_attachment()` (CRM adapter handles Claim Titan specifics)
4. Email marked as read

## Benefits of This Architecture

### 1. **Easy to Add New Clients**
```bash
# New client with same setup (Outlook + Claim Titan)
cp forerunner.env newclient.env
# Just change credentials, same adapters/modules

# New client with different setup (Gmail + Xactimate)
cp forerunner.env newclient.env
# Change EMAIL_ADAPTER=gmail, CRM_ADAPTER=xactimate
# Might need to build Xactimate adapter first
```

### 2. **Easy to Add New Features**
```python
# New module: PaymentTracking
# 1. Create src/modules/payment_tracking.py
# 2. Implement AutomationModule interface
# 3. Add to client config: ENABLED_MODULES=...,PaymentTracking
# Done! Works for all CRMs that support get_claim_state()
```

### 3. **Easy to Add New CRMs**
```python
# New CRM: Xactimate
# 1. Create src/adapters/crm/xactimate.py
# 2. Implement CRMAdapter interface
# 3. Add Playwright logic for Xactimate UI
# 4. Update config: CRM_ADAPTER=xactimate
# Done! All modules work with Xactimate now
```

### 4. **Easy to Test**
```python
# Test CommentAddition module with MockCRMAdapter
mock_crm = MockCRMAdapter()
comment_module = CommentAdditionModule(email_adapter, mock_crm, config)
comment_module.process(test_email)
# Verify mock_crm.post_note() was called
```

## Migration Path

### Phase 1: Refactor Current Code (This Week - Low Risk)
- Move `email_monitor.py` → `adapters/email/outlook.py`
- Move `claim_titan_bot.py` → `adapters/crm/claim_titan.py`
- Create `modules/comment_addition.py` (wraps current logic)
- Create `modules/attachment_upload.py` (wraps current logic)
- Create `modules/contract_parsing.py` (wraps current logic)
- Update `main.py` to use new structure

**Result:** Same functionality, better structure

### Phase 2: Add Configuration System (This Week - Low Risk)
- Create `config.py` with module loading
- Add `ENABLED_MODULES` to `.env`
- Test with Forerunner (should work identically)

**Result:** Can enable/disable features via config

### Phase 3: Deploy to New Client (When Needed)
- If same setup: Just copy config
- If different CRM: Build new adapter first
- If different features: Just change ENABLED_MODULES

**Result:** Multi-client support

### Phase 4: Add Intelligence Features (Future)
- Build `modules/risk_scoring.py`
- Build `modules/idle_claim_alerts.py`
- Enable for clients who want them

**Result:** Premium features available

## Risk Assessment

### Low Risk:
✅ Refactoring into adapters/modules (just moving code)
✅ Adding configuration system (additive change)
✅ Testing with current client (no behavior change)

### Medium Risk:
⚠️ Building new CRM adapter (time investment, need to learn UI)
⚠️ Building Gmail adapter (different auth, need testing)

### High Risk:
❌ Breaking current production system (mitigate with careful testing)
❌ Over-engineering before proving multi-client demand (mitigate by keeping it simple)

## Timeline

**Week 1: Refactor (6-8 hours)**
- Day 1-2: Create adapter interfaces and move code
- Day 3: Create module system
- Day 4: Update main.py orchestration
- Day 5: Test with Forerunner (should work identically)

**Week 2: Polish (2-4 hours)**
- Add better error handling
- Add logging
- Document configuration options
- Deploy to production

**Future: Add as Needed**
- Gmail adapter: 2-4 hours
- Xactimate adapter: 3-5 days
- New modules: 1-2 days each

## Questions to Decide

1. **Browser Pool:** Build now or later?
   - Recommendation: Build now (same week as refactor, only adds 2-3 hours)

2. **Database Migration:** SQLAlchemy now or later?
   - Recommendation: Build now (makes future Postgres migration easy, 3-4 hours)

3. **Intelligence Layer:** Build now or later?
   - Recommendation: Later (wait until client requests it)

## Next Steps

1. Review this architecture - does it make sense?
2. Decide on timeline (refactor this week? next week?)
3. Start with adapter interfaces
4. Move existing code into adapters
5. Build module system
6. Test with Forerunner
7. Deploy to production

---

**This architecture gives you maximum flexibility with minimum code duplication.**
