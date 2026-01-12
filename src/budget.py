"""
Budget management functionality.
"""
from datetime import date
from models import get_session, Budget, BudgetItem, Category, Transaction


class BudgetManager:
    """Manage budgets and budget items."""
    
    def __init__(self, user_id=1):
        self.user_id = user_id
    
    def get_budgets(self):
        """Get all budgets for the user."""
        session = get_session()
        try:
            budgets = session.query(Budget).filter_by(user_id=self.user_id).all()
            return [self._budget_to_dict(b) for b in budgets]
        finally:
            session.close()
    
    def get_budget(self, budget_id):
        """Get a specific budget with items."""
        session = get_session()
        try:
            budget = session.query(Budget).filter_by(
                id=budget_id, user_id=self.user_id
            ).first()
            
            if not budget:
                return None
            
            return self._budget_to_dict(budget, include_items=True)
        finally:
            session.close()
    
    def create_budget(self, name, items=None):
        """Create a new budget."""
        session = get_session()
        try:
            budget = Budget(
                user_id=self.user_id,
                name=name,
                period_type='monthly',
                is_active=True
            )
            session.add(budget)
            session.commit()
            
            if items:
                for item_data in items:
                    item = BudgetItem(
                        budget_id=budget.id,
                        category_id=item_data['category_id'],
                        budgeted_amount=item_data['amount'],
                        period=item_data.get('period', date.today().strftime('%Y-%m'))
                    )
                    session.add(item)
                session.commit()
            
            return {'id': budget.id, 'name': budget.name}
        finally:
            session.close()
    
    def create_from_averages(self, name, months=3):
        """Create a budget based on average spending."""
        session = get_session()
        try:
            # Calculate date range
            today = date.today()
            start_date = date(today.year, today.month, 1)
            for _ in range(months):
                if start_date.month == 1:
                    start_date = date(start_date.year - 1, 12, 1)
                else:
                    start_date = date(start_date.year, start_date.month - 1, 1)
            
            # Get category totals
            transactions = session.query(Transaction).filter(
                Transaction.user_id == self.user_id,
                Transaction.date >= start_date,
                Transaction.amount < 0
            ).all()
            
            category_totals = {}
            for t in transactions:
                if t.category:
                    cat_id = t.category_id
                    category_totals[cat_id] = category_totals.get(cat_id, 0) + abs(t.amount)
            
            # Create budget
            budget = Budget(
                user_id=self.user_id,
                name=name,
                period_type='monthly',
                is_active=True
            )
            session.add(budget)
            session.commit()
            
            # Create items from averages
            current_period = today.strftime('%Y-%m')
            for cat_id, total in category_totals.items():
                avg_amount = round(total / months, 2)
                if avg_amount > 0:
                    item = BudgetItem(
                        budget_id=budget.id,
                        category_id=cat_id,
                        budgeted_amount=avg_amount,
                        period=current_period
                    )
                    session.add(item)
            
            session.commit()
            return {'id': budget.id, 'name': budget.name}
        finally:
            session.close()
    
    def get_budget_status(self, budget_id, period=None):
        """Get budget vs actual status for a period."""
        if period is None:
            period = date.today().strftime('%Y-%m')
        
        session = get_session()
        try:
            budget = session.query(Budget).filter_by(
                id=budget_id, user_id=self.user_id
            ).first()
            
            if not budget:
                return None
            
            # Parse period
            year, month = map(int, period.split('-'))
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month + 1, 1)
            
            # Get actual spending by category
            # Note: Some transactions may have positive amounts (expenses) or negative (income)
            # We want all non-income transactions for budget tracking
            transactions = session.query(Transaction).filter(
                Transaction.user_id == self.user_id,
                Transaction.date >= start_date,
                Transaction.date < end_date
            ).all()
            
            actual_by_category = {}
            for t in transactions:
                cat_id = t.category_id
                # Use absolute value to handle both positive and negative expense amounts
                actual_by_category[cat_id] = actual_by_category.get(cat_id, 0) + abs(t.amount)
            
            # Build status for each budget item
            items_status = []
            for item in budget.items:
                if item.period != period:
                    continue
                
                actual = actual_by_category.get(item.category_id, 0)
                budgeted = item.budgeted_amount
                variance = budgeted - actual
                percent_used = (actual / budgeted * 100) if budgeted > 0 else 0
                
                items_status.append({
                    'category': item.category.name if item.category else 'Unknown',
                    'budgeted': round(budgeted, 2),
                    'actual': round(actual, 2),
                    'variance': round(variance, 2),
                    'percent_used': round(percent_used, 1)
                })
            
            # Sort by percent used descending
            items_status.sort(key=lambda x: x['percent_used'], reverse=True)
            
            return {
                'budget_name': budget.name,
                'period': period,
                'items': items_status,
                'total_budgeted': sum(i['budgeted'] for i in items_status),
                'total_actual': sum(i['actual'] for i in items_status)
            }
        finally:
            session.close()
    
    def _budget_to_dict(self, budget, include_items=False):
        """Convert budget to dictionary."""
        result = {
            'id': budget.id,
            'name': budget.name,
            'period_type': budget.period_type,
            'is_active': budget.is_active
        }
        
        if include_items:
            result['items'] = [
                {
                    'id': item.id,
                    'category': item.category.name if item.category else 'Unknown',
                    'category_id': item.category_id,
                    'budgeted_amount': item.budgeted_amount,
                    'period': item.period
                }
                for item in budget.items
            ]
        
        return result
