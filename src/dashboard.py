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
            
            # Get previous month comparison data
            prev_month_data = self._get_previous_month_comparison(user_id, year, month, session)
            
            # Generate quick insights
            insights = self._generate_quick_insights(summary, prev_month_data, by_category, top_merchants)
            
            return {
                'year': year,
                'month': month,
                'summary': summary,
                'by_category': by_category,
                'by_group': by_group,
                'top_merchants': top_merchants,
                'trends': trends,
                'comparison': prev_month_data,
                'insights': insights
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
    
    def _get_previous_month_comparison(self, user_id, year, month, session):
        """Get previous month data for comparison."""
        # Calculate previous month
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1
        
        # Get date range for previous month
        prev_start = date(prev_year, prev_month, 1)
        if prev_month == 12:
            prev_end = date(prev_year + 1, 1, 1)
        else:
            prev_end = date(prev_year, prev_month + 1, 1)
        
        # Get previous month transactions
        prev_transactions = session.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date >= prev_start,
            Transaction.date < prev_end
        ).all()
        
        # Calculate previous month summary
        excluded_ids = self._get_excluded_category_ids(session)
        prev_income = sum(t.amount for t in prev_transactions if t.amount > 0)
        prev_expenses = sum(
            abs(t.amount) for t in prev_transactions 
            if t.amount < 0 and t.category_id not in excluded_ids
        )
        prev_net = prev_income - prev_expenses
        prev_savings_rate = (prev_net / prev_income * 100) if prev_income > 0 else 0
        
        # Get previous month category breakdown
        prev_by_category = {}
        for t in prev_transactions:
            if t.amount >= 0 or t.category_id in excluded_ids:
                continue
            cat_name = t.category.name if t.category else 'Uncategorized'
            prev_by_category[cat_name] = prev_by_category.get(cat_name, 0) + abs(t.amount)
        
        return {
            'prev_year': prev_year,
            'prev_month': prev_month,
            'prev_month_name': date(prev_year, prev_month, 1).strftime('%B'),
            'income': round(prev_income, 2),
            'expenses': round(prev_expenses, 2),
            'net': round(prev_net, 2),
            'savings_rate': round(prev_savings_rate, 1),
            'by_category': prev_by_category
        }
    
    def _generate_quick_insights(self, current_summary, prev_data, by_category, top_merchants):
        """Generate quick insights based on spending patterns."""
        insights = []
        
        # Income change insight
        if prev_data['income'] > 0:
            income_change = ((current_summary['income'] - prev_data['income']) / prev_data['income']) * 100
            if income_change > 10:
                insights.append({
                    'type': 'positive',
                    'icon': 'bi-graph-up-arrow',
                    'title': 'Income Up',
                    'message': f"Income increased by {income_change:.0f}% from last month"
                })
            elif income_change < -10:
                insights.append({
                    'type': 'warning',
                    'icon': 'bi-graph-down-arrow',
                    'title': 'Income Down',
                    'message': f"Income decreased by {abs(income_change):.0f}% from last month"
                })
        
        # Expense change insight
        if prev_data['expenses'] > 0:
            expense_change = ((current_summary['expenses'] - prev_data['expenses']) / prev_data['expenses']) * 100
            if expense_change > 15:
                insights.append({
                    'type': 'warning',
                    'icon': 'bi-exclamation-triangle',
                    'title': 'Spending Up',
                    'message': f"Expenses increased by {expense_change:.0f}% from last month"
                })
            elif expense_change < -10:
                insights.append({
                    'type': 'positive',
                    'icon': 'bi-piggy-bank',
                    'title': 'Spending Down',
                    'message': f"You spent {abs(expense_change):.0f}% less than last month"
                })
        
        # Savings rate insight
        if current_summary['savings_rate'] >= 20:
            insights.append({
                'type': 'positive',
                'icon': 'bi-trophy',
                'title': 'Great Savings',
                'message': f"You're saving {current_summary['savings_rate']:.0f}% of your income!"
            })
        elif current_summary['savings_rate'] < 0:
            insights.append({
                'type': 'negative',
                'icon': 'bi-exclamation-circle',
                'title': 'Overspending',
                'message': "You spent more than you earned this month"
            })
        
        # Category change insights
        prev_by_cat = prev_data.get('by_category', {})
        for cat in by_category[:5]:  # Top 5 categories
            cat_name = cat['name']
            current_amt = cat['amount']
            prev_amt = prev_by_cat.get(cat_name, 0)
            
            if prev_amt > 0:
                cat_change = ((current_amt - prev_amt) / prev_amt) * 100
                if cat_change > 50 and current_amt > 100:
                    insights.append({
                        'type': 'warning',
                        'icon': 'bi-arrow-up-circle',
                        'title': f'{cat_name} Spike',
                        'message': f"{cat_name} spending up {cat_change:.0f}% (${current_amt:.0f} vs ${prev_amt:.0f})"
                    })
        
        # Top merchant insight
        if top_merchants:
            top = top_merchants[0]
            insights.append({
                'type': 'info',
                'icon': 'bi-shop',
                'title': 'Top Merchant',
                'message': f"Most spent at {top['name']}: ${top['amount']:.2f}"
            })
        
        return insights[:6]  # Return max 6 insights
