"""
Dashboard data generation and analytics.
"""
from datetime import date, timedelta
from sqlalchemy import func, extract
from models import get_session, Transaction, Category


class DashboardGenerator:
    """Generate dashboard analytics data."""
    
    # Categories to exclude from expense calculations (to prevent double-counting)
    EXCLUDED_CATEGORIES = ['Credit Card Payment', 'Transfer', 'CC Payment']
    
    def get_dashboard_data(self, year, month, user_id=1):
        """
        Get all dashboard data for a given month.
        
        Returns dict with summary, category breakdown, and chart data.
        """
        session = get_session()
        
        try:
            # Get date range
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month + 1, 1)
            
            # Get transactions for the month
            transactions = session.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.date >= start_date,
                Transaction.date < end_date
            ).all()
            
            # Calculate summary
            summary = self._calculate_summary(transactions, session)
            
            # Get category breakdown
            by_category = self._get_category_breakdown(transactions, session)
            
            # Get category group breakdown
            by_group = self._get_group_breakdown(transactions, session)
            
            # Get top merchants
            top_merchants = self._get_top_merchants(transactions)
            
            return {
                'year': year,
                'month': month,
                'summary': summary,
                'by_category': by_category,
                'by_group': by_group,
                'top_merchants': top_merchants
            }
        finally:
            session.close()
    
    def _calculate_summary(self, transactions, session):
        """Calculate summary statistics."""
        income = sum(t.amount for t in transactions if t.amount > 0)
        
        # Exclude credit card payments from expenses
        excluded_ids = self._get_excluded_category_ids(session)
        expenses = sum(
            abs(t.amount) for t in transactions 
            if t.amount < 0 and t.category_id not in excluded_ids
        )
        
        net = income - expenses
        savings_rate = (net / income * 100) if income > 0 else 0
        
        return {
            'income': round(income, 2),
            'expenses': round(expenses, 2),
            'net': round(net, 2),
            'savings_rate': round(savings_rate, 1),
            'transaction_count': len(transactions)
        }
    
    def _get_excluded_category_ids(self, session):
        """Get IDs of categories to exclude from expense calculations."""
        categories = session.query(Category).filter(
            Category.name.in_(self.EXCLUDED_CATEGORIES)
        ).all()
        return {c.id for c in categories}
    
    def _get_category_breakdown(self, transactions, session):
        """Get spending breakdown by category."""
        excluded_ids = self._get_excluded_category_ids(session)
        
        category_totals = {}
        for t in transactions:
            if t.amount >= 0 or t.category_id in excluded_ids:
                continue
            
            cat_name = t.category.name if t.category else 'Uncategorized'
            category_totals[cat_name] = category_totals.get(cat_name, 0) + abs(t.amount)
        
        # Sort by amount descending
        sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        
        return [{'name': name, 'amount': round(amt, 2)} for name, amt in sorted_cats]
    
    def _get_group_breakdown(self, transactions, session):
        """Get spending breakdown by category group."""
        excluded_ids = self._get_excluded_category_ids(session)
        
        group_totals = {}
        for t in transactions:
            if t.amount >= 0 or t.category_id in excluded_ids:
                continue
            
            group_name = t.category.group if t.category else 'Other'
            group_totals[group_name] = group_totals.get(group_name, 0) + abs(t.amount)
        
        sorted_groups = sorted(group_totals.items(), key=lambda x: x[1], reverse=True)
        
        return [{'name': name, 'amount': round(amt, 2)} for name, amt in sorted_groups]
    
    def _get_top_merchants(self, transactions, limit=10):
        """Get top merchants by spending."""
        from merchant_extractor import extract_merchant_name
        
        merchant_totals = {}
        
        for t in transactions:
            if t.amount >= 0:
                continue
            
            # Use merchant extractor for clean names
            merchant = extract_merchant_name(t.description) if t.description else 'Unknown'
            merchant_totals[merchant] = merchant_totals.get(merchant, 0) + abs(t.amount)
        
        sorted_merchants = sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)
        
        return [{'name': name, 'amount': round(amt, 2)} for name, amt in sorted_merchants[:limit]]
    
    def get_available_months(self, user_id=1):
        """Get list of months that have transactions."""
        session = get_session()
        
        try:
            results = session.query(
                extract('year', Transaction.date).label('year'),
                extract('month', Transaction.date).label('month')
            ).filter(
                Transaction.user_id == user_id
            ).distinct().order_by(
                extract('year', Transaction.date).desc(),
                extract('month', Transaction.date).desc()
            ).all()
            
            months = []
            for row in results:
                year = int(row.year)
                month = int(row.month)
                label = date(year, month, 1).strftime('%b %Y')
                months.append({'year': year, 'month': month, 'label': label})
            
            return months
        finally:
            session.close()
    
    def get_category_averages(self, months=3, user_id=1):
        """Get average spending by category over the last N months."""
        session = get_session()
        
        try:
            # Get date range
            today = date.today()
            start_date = date(today.year, today.month, 1)
            for _ in range(months):
                if start_date.month == 1:
                    start_date = date(start_date.year - 1, 12, 1)
                else:
                    start_date = date(start_date.year, start_date.month - 1, 1)
            
            # Get transactions
            transactions = session.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.date >= start_date,
                Transaction.amount < 0
            ).all()
            
            # Calculate totals by category
            excluded_ids = self._get_excluded_category_ids(session)
            category_totals = {}
            
            for t in transactions:
                if t.category_id in excluded_ids:
                    continue
                cat_name = t.category.name if t.category else 'Uncategorized'
                category_totals[cat_name] = category_totals.get(cat_name, 0) + abs(t.amount)
            
            # Calculate averages
            averages = {name: round(total / months, 2) for name, total in category_totals.items()}
            
            return averages
        finally:
            session.close()
