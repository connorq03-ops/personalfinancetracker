"""
Data persistence module for exporting/importing transaction data.
Ensures categorized transactions survive repo cloning and server restarts.
"""
import json
import os
from datetime import date, datetime
from models import get_session, Transaction, Category, User

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'transactions_backup.json')


def export_data():
    """Export all transactions and categories to JSON file."""
    session = get_session()
    
    try:
        # Export categories
        categories = session.query(Category).all()
        categories_data = [
            {
                'id': c.id,
                'name': c.name,
                'group': c.group,
                'user_id': c.user_id
            }
            for c in categories
        ]
        
        # Export transactions
        transactions = session.query(Transaction).all()
        transactions_data = [
            {
                'id': t.id,
                'user_id': t.user_id,
                'date': t.date.isoformat() if t.date else None,
                'description': t.description,
                'amount': float(t.amount) if t.amount else 0,
                'category_id': t.category_id,
                'source': t.source,
                'is_recurring': t.is_recurring
            }
            for t in transactions
        ]
        
        # Create data directory if needed
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        # Save to JSON
        data = {
            'exported_at': datetime.now().isoformat(),
            'categories': categories_data,
            'transactions': transactions_data
        }
        
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Exported {len(categories_data)} categories and {len(transactions_data)} transactions")
        print(f"  Saved to: {DATA_FILE}")
        
        return {
            'success': True,
            'categories': len(categories_data),
            'transactions': len(transactions_data),
            'file': DATA_FILE
        }
        
    finally:
        session.close()


def import_data(force=False):
    """
    Import transactions and categories from JSON backup.
    Only imports if database is empty (unless force=True).
    """
    if not os.path.exists(DATA_FILE):
        print(f"No backup file found at {DATA_FILE}")
        return {'success': False, 'error': 'No backup file found'}
    
    session = get_session()
    
    try:
        # Check if database already has data
        existing_transactions = session.query(Transaction).count()
        if existing_transactions > 0 and not force:
            print(f"Database already has {existing_transactions} transactions. Use force=True to overwrite.")
            return {'success': False, 'error': 'Database not empty', 'existing': existing_transactions}
        
        # Load backup data
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        print(f"Loading backup from {data.get('exported_at', 'unknown date')}...")
        
        # Ensure default user exists
        user = session.query(User).filter_by(id=1).first()
        if not user:
            user = User(id=1, email='default@example.com', name='Default User')
            session.add(user)
            session.commit()
        
        # Import categories first
        categories_imported = 0
        category_id_map = {}  # old_id -> new_id
        
        for cat_data in data.get('categories', []):
            # Check if category already exists
            existing = session.query(Category).filter_by(
                name=cat_data['name'],
                user_id=cat_data.get('user_id', 1)
            ).first()
            
            if existing:
                category_id_map[cat_data['id']] = existing.id
            else:
                category = Category(
                    name=cat_data['name'],
                    group=cat_data.get('group', 'Other'),
                    user_id=cat_data.get('user_id', 1)
                )
                session.add(category)
                session.flush()  # Get the ID
                category_id_map[cat_data['id']] = category.id
                categories_imported += 1
        
        session.commit()
        
        # Import transactions
        transactions_imported = 0
        transactions_skipped = 0
        
        for t_data in data.get('transactions', []):
            # Check for duplicate (same date, description, amount)
            t_date = date.fromisoformat(t_data['date']) if t_data.get('date') else None
            
            existing = session.query(Transaction).filter_by(
                date=t_date,
                description=t_data['description'],
                amount=t_data['amount'],
                user_id=t_data.get('user_id', 1)
            ).first()
            
            if existing:
                transactions_skipped += 1
                continue
            
            # Map old category ID to new
            new_category_id = category_id_map.get(t_data.get('category_id'))
            
            transaction = Transaction(
                user_id=t_data.get('user_id', 1),
                date=t_date,
                description=t_data['description'],
                amount=t_data['amount'],
                category_id=new_category_id,
                source=t_data.get('source'),
                is_recurring=t_data.get('is_recurring', False)
            )
            session.add(transaction)
            transactions_imported += 1
        
        session.commit()
        
        print(f"✓ Imported {categories_imported} new categories")
        print(f"✓ Imported {transactions_imported} transactions ({transactions_skipped} duplicates skipped)")
        
        return {
            'success': True,
            'categories_imported': categories_imported,
            'transactions_imported': transactions_imported,
            'transactions_skipped': transactions_skipped
        }
        
    except Exception as e:
        session.rollback()
        print(f"Error importing data: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        session.close()


def check_and_restore():
    """
    Check if database is empty and restore from backup if available.
    Called on app startup.
    """
    session = get_session()
    try:
        transaction_count = session.query(Transaction).count()
        
        if transaction_count == 0:
            print("Database is empty. Checking for backup...")
            if os.path.exists(DATA_FILE):
                print("Backup found! Restoring data...")
                return import_data()
            else:
                print("No backup found. Database will remain empty.")
                return {'success': False, 'error': 'No backup available'}
        else:
            print(f"Database has {transaction_count} transactions.")
            return {'success': True, 'existing': transaction_count}
    finally:
        session.close()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'export':
            export_data()
        elif command == 'import':
            force = '--force' in sys.argv
            import_data(force=force)
        elif command == 'check':
            check_and_restore()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python data_persistence.py [export|import|check]")
    else:
        print("Usage: python data_persistence.py [export|import|check]")
        print("  export - Export database to JSON backup")
        print("  import - Import from JSON backup (only if DB is empty)")
        print("  import --force - Force import even if DB has data")
        print("  check  - Check DB and restore from backup if empty")
