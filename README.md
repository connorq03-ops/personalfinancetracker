# Personal Finance Tracker

A web-based personal finance application that imports bank statements, automatically categorizes transactions using machine learning, and provides visual spending analytics.

## Features

- **Transaction Import** - Upload PDF/CSV statements from Bank of America, Robinhood, Venmo
- **ML Categorization** - Automatic transaction categorization using TF-IDF + Naive Bayes
- **Visual Dashboard** - Interactive charts showing spending by category, trends, and insights
- **Budget Tracking** - Create budgets based on spending history and track progress
- **Multi-Bank Support** - Extensible parser system for different bank formats

## Tech Stack

- **Backend**: Python 3, Flask, SQLAlchemy, SQLite
- **Frontend**: Bootstrap 5, Chart.js, Vanilla JavaScript
- **ML**: scikit-learn (TF-IDF + Naive Bayes)
- **Data Processing**: Pandas, pdfplumber

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/personal-finance-tracker.git
cd personal-finance-tracker

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python3 src/models.py

# Run the application
python3 src/app.py
```

Then open http://localhost:5000 in your browser.

## Project Structure

```
personal-finance-tracker/
├── src/
│   ├── app.py                 # Main Flask application
│   ├── models.py              # SQLAlchemy database models
│   ├── dashboard.py           # Dashboard data calculations
│   ├── categorizer.py         # ML transaction categorization
│   ├── parsers/
│   │   ├── boa_parser.py      # Bank of America PDF parser
│   │   ├── robinhood_parser.py # Robinhood CSV parser
│   │   └── venmo_parser.py    # Venmo CSV parser
│   └── budget.py              # Budget management
├── templates/
│   ├── base.html              # Base template with navigation
│   ├── transactions.html      # Transaction list view
│   ├── dashboard.html         # Analytics dashboard
│   ├── budget.html            # Budget management
│   └── upload.html            # File upload page
├── static/
│   ├── css/
│   │   └── style.css          # Custom styles
│   └── js/
│       └── app.js             # Frontend JavaScript
├── uploads/                   # Temporary upload storage
├── requirements.txt           # Python dependencies
└── README.md
```

## Usage

### Importing Transactions

1. Navigate to the **Upload** page
2. Drag and drop your bank statement (PDF or CSV)
3. Transactions are automatically parsed and categorized

### Managing Categories

- Click on any transaction's category badge to change it
- The ML model learns from your corrections
- New transactions will be categorized more accurately over time

### Creating a Budget

1. Go to the **Budget** page
2. Click "Create Budget from Averages" to use your 3-month spending history
3. Adjust amounts as needed
4. Track your progress throughout the month

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/transactions` | List transactions with filters |
| POST | `/api/transactions/<id>/category` | Update transaction category |
| GET | `/api/categories` | List all categories |
| GET | `/dashboard` | Analytics dashboard |
| GET | `/api/dashboard/<year>/<month>` | Dashboard data JSON |
| POST | `/api/upload/boa` | Upload Bank of America PDF |
| POST | `/api/upload/robinhood` | Upload Robinhood CSV |
| GET | `/api/budgets` | List budgets |
| POST | `/api/budgets` | Create new budget |

## License

MIT License - feel free to use and modify for your personal use.

## Contributing

Contributions welcome! Please open an issue or submit a pull request.
