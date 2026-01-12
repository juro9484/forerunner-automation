# forerunner-automation
Automated email-to-CRM claim note system for insurance clients

# Forerunner Claims - Email to CRM Automation

Automated system for processing insurance claim emails and posting AI-generated summaries to Claim Titan CRM.

## 🎯 Project Goal
Replace manual VA work by automating:
1. Email monitoring (claim-related messages)
2. Claim number extraction
3. AI-powered email summarization
4. Automatic note posting to Claim Titan

## 📊 Current Status
- [ ] MVP Development (Target: 4 weeks)
- [ ] Client: Forerunner Claims (Insurance)
- [ ] Estimated savings: TBD based on VA hours saved

## 🛠 Tech Stack
- **Language:** Python 3.11+
- **Web Automation:** Selenium/Playwright
- **AI:** OpenAI GPT-4 or Anthropic Claude
- **Email:** IMAP/Gmail API
- **Hosting:** On-prem ZBook (will migrate to AWS later)

## 📁 Project Structure
```
claim-automation/
├── src/
│   ├── email_monitor.py      # Email checking
│   ├── claim_titan_bot.py    # Web automation
│   ├── summarizer.py          # AI summarization
│   └── main.py                # Main orchestrator
├── tests/
├── logs/
├── docs/
├── .env.example               # Template for credentials
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Chrome browser (for Selenium)
- Active Claim Titan account

### Installation
```bash
# Clone the repo
git clone https://github.com/yourusername/claim-automation.git
cd claim-automation

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Copy environment template and fill in credentials
copy .env.example .env
# Edit .env with your actual credentials
```

### Configuration
Create `.env` file with:
```
CLAIM_TITAN_USER=your_email
CLAIM_TITAN_PASS=your_password
OPENAI_API_KEY=sk-...
```

### Run
```bash
python src/main.py
```

## 📝 Development Workflow

### Branching Strategy
- `main` - Production-ready code
- `develop` - Active development
- `feature/feature-name` - New features

### Making Changes
```bash
# Create feature branch
git checkout -b feature/email-monitor

# Make changes, commit often
git add .
git commit -m "Add email monitoring logic"

# Push to GitHub
git push origin feature/email-monitor

# Create Pull Request on GitHub for review
```

## 🔒 Security Notes
- **NEVER commit `.env` files**
- All credentials in environment variables
- `.gitignore` is already configured
- Use strong passwords for bot accounts

## 📚 Documentation
- [Setup Guide](docs/setup_guide.md)
- [Architecture](docs/architecture.md)
- [Security Best Practices](docs/security.md)
- [Client Onboarding](docs/client_onboarding.md)

## 🐛 Known Issues
- [ ] Claim Titan may have rate limiting (TBD)
- [ ] Need to handle CAPTCHA if present

## 📈 Roadmap
- [x] Project setup
- [ ] Email monitoring module
- [ ] Claim Titan automation
- [ ] AI summarization
- [ ] End-to-end testing
- [ ] Production deployment
- [ ] Multi-client support

## 👥 Team
- **Developer 1:** [Your Name]
- **Developer 2:** [Boss's Name]
- **Client Contact:** Beau @ Forerunner Claims

## 📄 License
Proprietary - Not for public distribution

## 🤝 Contributing
This is a private business project. All code is confidential.
