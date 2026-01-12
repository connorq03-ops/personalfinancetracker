"""
Personal Finance Tracker - Main Flask Application
"""
import os
import sys
from datetime import date
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import init_db, get_session, Transaction, Category, User
from categorizer import get_categorizer
from dashboard import DashboardGenerator
from budget import BudgetManager
from parsers.boa_parser import BoAParser
from parsers.robinhood_parser import RobinhoodParser
from parsers.venmo_parser import VenmoParser
import merchant_extractor

# Initialize Flask app
app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')
CORS(app)

# Configuration
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'finances.db')
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')

# Initialize database
init_db(DB_PATH)

# Initialize services
dashboard_gen = DashboardGenerator()
budget_manager = BudgetManager()
categorizer = get_categorizer()

# Register Jinja2 filters
merchant_extractor.init_app(app)


# =============================================================================
# ROUTES - Pages
# =============================================================================

@app.route('/')
def index():
    """Redirect to transactions page."""
    return redirect(url_for('transactions'))


@app.route('/transactions')
def transactions():
    """Transaction list page."""
    session = get_session()
    try:
        # Get filter parameters
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        category_id = request.args.get('category', type=int)
        search = request.args.get('search', '')
        
        # Get available months first
        available_months = dashboard_gen.get_available_months()
        
        # Default to most recent month with data, or current month if no data
        if not year or not month:
            if available_months:
                year = available_months[0]['year']
                month = available_months[0]['month']
            else:
                today = date.today()
                year = today.year
                month = today.month
        
        # Build query
        query = session.query(Transaction).filter(Transaction.user_id == 1)
        
        # Date filter
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        query = query.filter(
            Transaction.date >= start_date,
            Transaction.date < end_date
        )
        
        # Category filter
        if category_id:
            query = query.filter(Transaction.category_id == category_id)
        
        # Search filter
        if search:
            query = query.filter(Transaction.description.ilike(f'%{search}%'))
        
        # Execute query
        transactions_list = query.order_by(Transaction.date.desc()).all()
        
        # Calculate summary
        total_income = sum(t.amount for t in transactions_list if t.amount > 0)
        total_expenses = sum(abs(t.amount) for t in transactions_list if t.amount < 0)
        
        summary = {
            'income': total_income,
            'expenses': total_expenses,
            'net': total_income - total_expenses,
            'count': len(transactions_list)
        }
        
        # Get categories for filter (alphabetical order)
        categories = session.query(Category).filter_by(user_id=1).order_by(Category.name).all()
        
        return render_template('transactions.html',
                             transactions=transactions_list,
                             categories=categories,
                             summary=summary,
                             year=year,
                             month=month,
                             month_name=date(year, month, 1).strftime('%B'),
                             category_id=category_id,
                             search=search,
                             available_months=available_months)
    finally:
        session.close()


@app.route('/dashboard')
def dashboard():
    """Analytics dashboard page."""
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    available_months = dashboard_gen.get_available_months()
    
    # Default to most recent month with data
    if not year or not month:
        if available_months:
            year = available_months[0]['year']
            month = available_months[0]['month']
        else:
            today = date.today()
            year = today.year
            month = today.month
    
    data = dashboard_gen.get_dashboard_data(year, month)
    
    return render_template('dashboard.html',
                         data=data,
                         year=year,
                         month=month,
                         month_name=date(year, month, 1).strftime('%B'),
                         available_months=available_months)


@app.route('/budget')
def budget():
    """Budget management page."""
    budgets = budget_manager.get_budgets()
    
    # Get active budget status
    active_budget = next((b for b in budgets if b.get('is_active')), None)
    budget_status = None
    if active_budget:
        budget_status = budget_manager.get_budget_status(active_budget['id'])
    
    return render_template('budget.html',
                         budgets=budgets,
                         budget_status=budget_status)


@app.route('/upload')
def upload():
    """File upload page."""
    return render_template('upload.html')


# =============================================================================
# API - Transactions
# =============================================================================

@app.route('/api/transactions/<int:transaction_id>/category', methods=['POST'])
def update_transaction_category(transaction_id):
    """Update a transaction's category."""
    session = get_session()
    try:
        data = request.get_json()
        category_id = data.get('category_id')
        
        transaction = session.query(Transaction).filter_by(id=transaction_id).first()
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        transaction.category_id = category_id
        session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/categories')
def get_categories():
    """Get all categories."""
    session = get_session()
    try:
        categories = session.query(Category).filter_by(user_id=1).order_by(Category.group, Category.name).all()
        return jsonify([c.to_dict() for c in categories])
    finally:
        session.close()


@app.route('/api/categories', methods=['POST'])
def create_category():
    """Create a new category."""
    session = get_session()
    try:
        data = request.get_json()
        
        category = Category(
            name=data['name'],
            group=data.get('group', 'Other'),
            user_id=1
        )
        session.add(category)
        session.commit()
        
        return jsonify(category.to_dict())
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


# =============================================================================
# API - Dashboard
# =============================================================================

@app.route('/api/dashboard/<int:year>/<int:month>')
def get_dashboard_data(year, month):
    """Get dashboard data as JSON."""
    data = dashboard_gen.get_dashboard_data(year, month)
    return jsonify(data)


@app.route('/api/dashboard/averages')
def get_category_averages():
    """Get category spending averages."""
    months = request.args.get('months', 3, type=int)
    averages = dashboard_gen.get_category_averages(months)
    return jsonify(averages)


# =============================================================================
# API - Budget
# =============================================================================

@app.route('/api/budgets')
def get_budgets():
    """Get all budgets."""
    budgets = budget_manager.get_budgets()
    return jsonify(budgets)


@app.route('/api/budgets', methods=['POST'])
def create_budget():
    """Create a new budget."""
    data = request.get_json()
    
    if data.get('from_averages'):
        result = budget_manager.create_from_averages(
            data['name'],
            data.get('months', 3)
        )
    else:
        result = budget_manager.create_budget(
            data['name'],
            data.get('items', [])
        )
    
    return jsonify(result)


@app.route('/api/budgets/<int:budget_id>')
def get_budget(budget_id):
    """Get a specific budget."""
    budget = budget_manager.get_budget(budget_id)
    if not budget:
        return jsonify({'error': 'Budget not found'}), 404
    return jsonify(budget)


@app.route('/api/budgets/<int:budget_id>/status')
def get_budget_status(budget_id):
    """Get budget vs actual status."""
    period = request.args.get('period')
    status = budget_manager.get_budget_status(budget_id, period)
    if not status:
        return jsonify({'error': 'Budget not found'}), 404
    return jsonify(status)


# =============================================================================
# API - File Upload
# =============================================================================

@app.route('/api/upload/boa', methods=['POST'])
def upload_boa():
    """Upload Bank of America PDF statement."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'File must be a PDF'}), 400
    
    # Save file temporarily
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    
    try:
        parser = BoAParser()
        transactions = parser.parse_statement(filepath)
        imported = _import_transactions(transactions)
        
        return jsonify({
            'success': True,
            'message': f'Imported {imported} transactions',
            'count': imported
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route('/api/upload/robinhood', methods=['POST'])
def upload_robinhood():
    """Upload Robinhood CSV file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    
    try:
        parser = RobinhoodParser()
        transactions = parser.parse_csv(filepath)
        imported = _import_transactions(transactions)
        
        return jsonify({
            'success': True,
            'message': f'Imported {imported} transactions',
            'count': imported
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route('/api/upload/venmo', methods=['POST'])
def upload_venmo():
    """Upload Venmo CSV file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    
    try:
        parser = VenmoParser()
        transactions = parser.parse_csv(filepath)
        imported = _import_transactions(transactions)
        
        return jsonify({
            'success': True,
            'message': f'Imported {imported} transactions',
            'count': imported
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


def _import_transactions(transactions_data):
    """Import parsed transactions into database."""
    session = get_session()
    imported_count = 0
    
    try:
        # Get categories lookup
        categories = {c.name: c.id for c in session.query(Category).filter_by(user_id=1).all()}
        uncategorized_id = categories.get('Uncategorized', 1)
        
        for t_data in transactions_data:
            # Check for duplicates
            existing = session.query(Transaction).filter_by(
                date=t_data['date'],
                description=t_data['description'],
                amount=t_data['amount'],
                user_id=1
            ).first()
            
            if existing:
                continue
            
            # Auto-categorize
            predicted = categorizer.predict(t_data['description'])
            category_id = categories.get(predicted, uncategorized_id)
            
            # Create transaction
            transaction = Transaction(
                user_id=1,
                date=t_data['date'],
                description=t_data['description'],
                amount=t_data['amount'],
                source=t_data.get('source'),
                raw_category=t_data.get('raw_category'),
                category_id=category_id
            )
            session.add(transaction)
            imported_count += 1
        
        session.commit()
        return imported_count
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Personal Finance Tracker")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print("Starting server on http://localhost:5001")
    print("=" * 60 + "\n")
    
    app.run(host='0.0.0.0', port=5001, debug=True)
