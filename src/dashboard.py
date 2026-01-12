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
            
            # Get spending trends (last 6 months)
            trends = self._get_spending_trends(user_id, year, month)
            
            return {
                'year': year,
                'month': month,
                'summary': summary,
                'by_category': by_category,
                'by_group': by_group,
                'top_merchants': top_merchants,
                'trends': trends
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
    
    def _get_spending_trends(self, user_id, current_year, current_month, num_months=6):
        """Get spending trends for the last N months."""
        session = get_session()
        try:
            trends = []
            excluded_ids = self._get_excluded_category_ids(session)
            
            for i in range(num_months - 1, -1, -1):
                # Calculate month offset
                month = current_month - i
                year = current_year
                while month <= 0:
                    month += 12
                    year -= 1
                
                # Get date range
                start_date = date(year, month, 1)
                if month == 12:
                    end_date = date(year + 1, 1, 1)
                else:
                    end_date = date(year, month + 1, 1)
                
                # Get transactions
                transactions = session.query(Transaction).filter(
                    Transaction.user_id == user_id,
                    Transaction.date >= start_date,
                    Transaction.date < end_date
                ).all()
                
                income = sum(t.amount for t in transactions if t.amount > 0)
                expenses = sum(abs(t.amount) for t in transactions 
                              if t.amount < 0 and t.category_id not in excluded_ids)
                
                trends.append({
                    'month': start_date.strftime('%b'),
                    'year': year,
                    'income': round(income, 2),
                    'expenses': round(expenses, 2),
                    'net': round(income - expenses, 2)
                })
            
            return trends
        finally:
            session.close()
    
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
    
    # Known recurring/fixed expense keywords for automatic detection
    RECURRING_KEYWORDS = {
        'rent', 'mortgage', 'truist', 'housing', 'utilities', 'electric', 'water', 'gas',
        'internet', 'wifi', 'cable', 'phone', 'mobile', 'cell',
        'spotify', 'netflix', 'hulu', 'hbo', 'disney', 'amazon prime', 'prime',
        'youtube', 'paramount', 'apple', 'microsoft', 'chatgpt', 'canva', 'adobe',
        'insurance', 'ymca', 'gym', 'fitness', 'membership',
        'car', 'auto', 'vehicle', 'tolls', 'parking',
        'loan', 'payment', 'sierra', 'hair', 'beauty', 'grooming', 'subscriptions'
    }
    
    def _is_recurring_category(self, category_name):
        """Check if category matches known recurring expense patterns."""
        cat_lower = category_name.lower()
        for keyword in self.RECURRING_KEYWORDS:
            if keyword in cat_lower:
                return True
        return False
    
    def get_category_averages(self, months=3, user_id=1):
        """Get average spending by category over the last N months with recurring status."""
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
            
            # Get user-marked recurring categories
            user_marked_recurring = set()
            recurring_transactions = session.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.is_recurring == True
            ).all()
            for t in recurring_transactions:
                if t.category and t.category.name:
                    user_marked_recurring.add(t.category.name)
            
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
            
            # Build result with recurring status
            result = {}
            for name, total in category_totals.items():
                is_recurring = name in user_marked_recurring or self._is_recurring_category(name)
                result[name] = {
                    'average': round(total / months, 2),
                    'is_recurring': is_recurring,
                    'user_marked': name in user_marked_recurring
                }
            
            return result
        finally:
            session.close()
    
    def get_category_monthly_pattern(self, category_name, user_id=1):
        """Get monthly spending pattern for a specific category."""
        session = get_session()
        
        try:
            # Find category
            category = session.query(Category).filter(
                Category.name == category_name,
                Category.user_id == user_id
            ).first()
            
            if not category:
                return None
            
            # Get all transactions for this category
            transactions = session.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == category.id,
                Transaction.amount < 0
            ).order_by(Transaction.date.desc()).all()
            
            # Group by month
            monthly_data = {}
            for t in transactions:
                month_key = t.date.strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = {'total': 0, 'count': 0, 'transactions': []}
                monthly_data[month_key]['total'] += abs(t.amount)
                monthly_data[month_key]['count'] += 1
                monthly_data[month_key]['transactions'].append({
                    'date': t.date.isoformat(),
                    'description': t.description,
                    'amount': abs(t.amount),
                    'is_recurring': t.is_recurring
                })
            
            # Calculate statistics
            if monthly_data:
                totals = [m['total'] for m in monthly_data.values()]
                avg = sum(totals) / len(totals)
                min_val = min(totals)
                max_val = max(totals)
            else:
                avg = min_val = max_val = 0
            
            # Check if user marked any as recurring
            has_recurring = any(
                t.is_recurring for t in transactions
            )
            
            return {
                'category': category_name,
                'months': monthly_data,
                'statistics': {
                    'average': round(avg, 2),
                    'min': round(min_val, 2),
                    'max': round(max_val, 2),
                    'months_with_data': len(monthly_data)
                },
                'is_recurring': has_recurring
            }
        finally:
            session.close()
    
    def get_all_category_patterns(self, user_id=1):
        """Get monthly spending patterns for all categories."""
        session = get_session()
        
        try:
            excluded_ids = self._get_excluded_category_ids(session)
            
            # Get all expense transactions grouped by category and month
            transactions = session.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.amount < 0
            ).all()
            
            # Build category patterns
            category_data = {}
            for t in transactions:
                if t.category_id in excluded_ids:
                    continue
                
                cat_name = t.category.name if t.category else 'Uncategorized'
                month_key = t.date.strftime('%Y-%m')
                
                if cat_name not in category_data:
                    category_data[cat_name] = {
                        'months': {},
                        'has_recurring': False
                    }
                
                if month_key not in category_data[cat_name]['months']:
                    category_data[cat_name]['months'][month_key] = 0
                
                category_data[cat_name]['months'][month_key] += abs(t.amount)
                
                if t.is_recurring:
                    category_data[cat_name]['has_recurring'] = True
            
            # Calculate statistics for each category
            result = {}
            for cat_name, data in category_data.items():
                monthly_totals = list(data['months'].values())
                if monthly_totals:
                    avg = sum(monthly_totals) / len(monthly_totals)
                    result[cat_name] = {
                        'months': data['months'],
                        'average': round(avg, 2),
                        'min': round(min(monthly_totals), 2),
                        'max': round(max(monthly_totals), 2),
                        'months_count': len(monthly_totals),
                        'is_recurring': data['has_recurring'] or self._is_recurring_category(cat_name)
                    }
            
            return result
        finally:
            session.close()
