"""
Advanced Analytics Engine for Personal Finance Tracker

KEY PRINCIPLES:
1. DOUBLE-COUNTING PREVENTION: CC payments from BoA are excluded
2. INVESTMENT TRANSFERS: Round-number transfers to Robinhood are investments
3. LIFE EVENTS: House purchase (Oct 2025) causes temporary spending spikes
4. COMMISSION INCOME: Base ~$5500/paycheck + variable commission
5. BUDGET INTEGRATION: Learn from user's budget to provide smarter insights
"""

import numpy as np
import re
from datetime import date, timedelta
from calendar import monthrange
from models import get_session, Transaction, Category, Budget, BudgetItem
from collections import defaultdict


class AdvancedAnalytics:
    """Advanced analytics with budget integration."""
    
    INCOME_CONFIG = {
        'base_per_paycheck': 5500,
        'paychecks_per_month': 2,
        'expected_base_monthly': 11000,
        'commission_quarterly_min': 40000,
        'commission_quarterly_max': 150000,
        'employer_pattern': 'exafunct',
    }
    
    LIFE_EVENTS = {
        'house_purchase': {
            'date': date(2025, 10, 1),
            'description': 'House purchase',
            'impact_months': 3,
            'categories_affected': ['Mortgage', 'Furniture', 'Home', 'Utilities', 'Natural Gas']
        }
    }
    
    EXCLUDED_EXPENSE_CATEGORIES = [
        'Credit Card Payment', 'Robinhood CC', 'Chase CC', 'Tally',
        'Transfer', 'Wire Transfer', 'Investments', 'Savings',
        'PayPal', 'Venmo',
    ]
    
    ONE_TIME_CATEGORIES = ['Furniture', 'Home', 'Vacation', 'Travel']
    
    def __init__(self):
        self.cc_payment_patterns = [
            r'payment.*thank you',
            r'robinhood card.*payment',
            r'chase credit crd',
            r'discover.*e-payment',
        ]
        self.investment_patterns = [
            r'robinhood des:funds',
            r'fid bkg svc',
            r'vanguard',
            r'schwab',
        ]
        self._budget_cache = None
        self._budget_cache_time = None
    
    def _get_active_budget(self, session, user_id=1):
        """Get the active budget with items."""
        # Cache for 5 minutes
        now = date.today()
        if self._budget_cache and self._budget_cache_time == now:
            return self._budget_cache
        
        budget = session.query(Budget).filter_by(
            user_id=user_id, is_active=True
        ).first()
        
        if not budget:
            return None
        
        # Get budget items with category names
        items = session.query(BudgetItem, Category).join(
            Category, BudgetItem.category_id == Category.id
        ).filter(BudgetItem.budget_id == budget.id).all()
        
        budget_data = {
            'id': budget.id,
            'name': budget.name,
            'total_budgeted': sum(item.budgeted_amount for item, _ in items),
            'items': {},
            'items_by_id': {}
        }
        
        for item, cat in items:
            budget_data['items'][cat.name.lower()] = {
                'category_id': cat.id,
                'category_name': cat.name,
                'budgeted_amount': item.budgeted_amount,
                'period': item.period
            }
            budget_data['items_by_id'][cat.id] = {
                'category_name': cat.name,
                'budgeted_amount': item.budgeted_amount,
                'period': item.period
            }
        
        self._budget_cache = budget_data
        self._budget_cache_time = now
        return budget_data
    
    def _is_cc_payment(self, description):
        desc_lower = (description or '').lower()
        for pattern in self.cc_payment_patterns:
            if re.search(pattern, desc_lower):
                return True
        return False
    
    def _is_investment_transfer(self, transaction):
        desc_lower = (transaction.description or '').lower()
        for pattern in self.investment_patterns:
            if re.search(pattern, desc_lower):
                return True
        if 'robinhood' in desc_lower and 'card' not in desc_lower:
            amt = abs(transaction.amount)
            if amt >= 500 and amt % 500 == 0:
                return True
            if amt >= 5000:
                return True
        return False
    
    def _is_paycheck(self, transaction):
        if transaction.amount <= 0:
            return False
        desc_lower = (transaction.description or '').lower()
        return self.INCOME_CONFIG['employer_pattern'] in desc_lower
    
    def _classify_income(self, amount):
        base = self.INCOME_CONFIG['base_per_paycheck']
        if abs(amount - base) / base < 0.20:
            return 'base'
        elif amount > base * 2:
            return 'commission'
        else:
            return 'base'
    
    def _get_excluded_category_ids(self, session):
        cats = session.query(Category).filter(
            Category.name.in_(self.EXCLUDED_EXPENSE_CATEGORIES)
        ).all()
        return {c.id for c in cats}
    
    def _is_actual_spending(self, transaction, category_name, excluded_ids):
        if transaction.category_id in excluded_ids:
            return False
        if category_name in self.EXCLUDED_EXPENSE_CATEGORIES:
            return False
        if self._is_cc_payment(transaction.description):
            return False
        if self._is_investment_transfer(transaction):
            return False
        return True
    
    def _is_in_life_event_period(self, txn_date, event_key):
        event = self.LIFE_EVENTS.get(event_key)
        if not event:
            return False
        event_date = event['date']
        impact_end = date(
            event_date.year + (event_date.month + event['impact_months'] - 1) // 12,
            (event_date.month + event['impact_months'] - 1) % 12 + 1,
            1
        )
        return event_date <= txn_date < impact_end
    
    def _get_life_event_context(self, txn_date, category_name):
        for event_key, event in self.LIFE_EVENTS.items():
            if self._is_in_life_event_period(txn_date, event_key):
                if category_name in event.get('categories_affected', []):
                    return event['description']
        return None
    
    def get_financial_health_score(self, user_id=1):
        """Calculate financial health with budget awareness."""
        session = get_session()
        try:
            today = date.today()
            excluded_ids = self._get_excluded_category_ids(session)
            budget = self._get_active_budget(session, user_id)
            
            months_data = []
            
            for i in range(4):
                if i == 0:
                    month_start = date(today.year, today.month, 1)
                    month_end = today
                    days_in_month = monthrange(today.year, today.month)[1]
                    completeness = today.day / days_in_month
                else:
                    target_month = today.month - i
                    target_year = today.year
                    while target_month <= 0:
                        target_month += 12
                        target_year -= 1
                    month_start = date(target_year, target_month, 1)
                    days_in_month = monthrange(target_year, target_month)[1]
                    month_end = date(target_year, target_month, days_in_month)
                    completeness = 1.0
                
                transactions = session.query(Transaction).filter(
                    Transaction.user_id == user_id,
                    Transaction.date >= month_start,
                    Transaction.date <= month_end
                ).all()
                
                if transactions:
                    base_income = 0
                    commission_income = 0
                    other_income = 0
                    recurring_expenses = 0
                    one_time_expenses = 0
                    investments = 0
                    house_related = 0
                    
                    # Track spending by category for budget comparison
                    category_spending = defaultdict(float)
                    
                    for t in transactions:
                        cat = session.query(Category).filter_by(id=t.category_id).first()
                        cat_name = cat.name if cat else 'Uncategorized'
                        
                        if t.amount > 0:
                            if self._is_paycheck(t):
                                if self._classify_income(t.amount) == 'base':
                                    base_income += t.amount
                                else:
                                    commission_income += t.amount
                            else:
                                other_income += t.amount
                        elif self._is_investment_transfer(t):
                            investments += abs(t.amount)
                        elif self._is_actual_spending(t, cat_name, excluded_ids):
                            amt = abs(t.amount)
                            category_spending[cat_name] += amt
                            
                            if self._get_life_event_context(t.date, cat_name) == 'House purchase':
                                house_related += amt
                            if cat_name in self.ONE_TIME_CATEGORIES:
                                one_time_expenses += amt
                            else:
                                recurring_expenses += amt
                    
                    if completeness <= 0.3 and i == 0:
                        continue
                    
                    total_income = base_income + commission_income + other_income
                    
                    if completeness < 1.0 and completeness > 0.3:
                        base_income = base_income / completeness
                        commission_income = commission_income / completeness
                        other_income = other_income / completeness
                        total_income = total_income / completeness
                        recurring_expenses = recurring_expenses / completeness
                        one_time_expenses = one_time_expenses / completeness
                        investments = investments / completeness
                        house_related = house_related / completeness
                        category_spending = {k: v / completeness for k, v in category_spending.items()}
                    
                    months_data.append({
                        'month': month_start.strftime('%Y-%m'),
                        'base_income': base_income,
                        'commission_income': commission_income,
                        'other_income': other_income,
                        'total_income': total_income,
                        'recurring_expenses': recurring_expenses,
                        'one_time_expenses': one_time_expenses,
                        'total_expenses': recurring_expenses + one_time_expenses,
                        'investments': investments,
                        'house_related': house_related,
                        'category_spending': dict(category_spending),
                        'completeness': completeness,
                        'in_house_event': self._is_in_life_event_period(month_start, 'house_purchase')
                    })
            
            if len(months_data) < 2:
                return {
                    "score": 0, "grade": "N/A", "factors": {},
                    "recommendations": [{"priority": "info", "message": "Need at least 2 months of data"}],
                    "data_quality": "insufficient"
                }
            
            factors = {}
            
            # 1. Savings Rate (25%)
            savings_rates = []
            for m in months_data:
                if m['total_income'] > 0:
                    savings = m['total_income'] - m['total_expenses']
                    rate = (savings / m['total_income']) * 100
                    savings_rates.append((max(-50, min(70, rate)), m['completeness']))
            
            if savings_rates:
                total_weight = sum(w for _, w in savings_rates)
                avg_savings_rate = sum(r * w for r, w in savings_rates) / total_weight
                savings_score = max(0, min(100, (avg_savings_rate + 10) * 1.8))
            else:
                avg_savings_rate, savings_score = 0, 0
            
            factors['savings_rate'] = {
                'value': round(avg_savings_rate, 1),
                'score': round(savings_score, 1),
                'weight': 0.25,
                'description': 'Income minus spending',
                'status': 'good' if savings_score >= 70 else 'fair' if savings_score >= 40 else 'poor'
            }
            
            # 2. Base Income Coverage (20%)
            coverage_scores = []
            expected_base = self.INCOME_CONFIG['expected_base_monthly']
            
            for m in months_data:
                if m['completeness'] >= 0.5:
                    base = m['base_income'] if m['base_income'] > 0 else expected_base
                    recurring = m['recurring_expenses']
                    if recurring > 0:
                        coverage_ratio = base / recurring
                        coverage_score = min(100, coverage_ratio * 100)
                        coverage_scores.append((coverage_score, m['completeness']))
            
            if coverage_scores:
                total_weight = sum(w for _, w in coverage_scores)
                avg_coverage = sum(s * w for s, w in coverage_scores) / total_weight
            else:
                avg_coverage = 50
            
            factors['base_coverage'] = {
                'value': round(avg_coverage, 1),
                'score': round(avg_coverage, 1),
                'weight': 0.20,
                'description': 'Base salary covers recurring expenses',
                'status': 'good' if avg_coverage >= 80 else 'fair' if avg_coverage >= 50 else 'poor'
            }
            
            # 3. Budget Adherence (25%) - NEW: Compare actual vs budgeted
            budget_scores = []
            budget_insights = []
            
            if budget:
                for m in months_data:
                    if m['completeness'] >= 0.5:
                        categories_on_budget = 0
                        categories_over = 0
                        categories_under = 0
                        total_budgeted = 0
                        total_actual = 0
                        over_budget_cats = []
                        
                        for cat_name, actual in m['category_spending'].items():
                            budget_item = budget['items'].get(cat_name.lower())
                            if budget_item:
                                budgeted = budget_item['budgeted_amount']
                                total_budgeted += budgeted
                                total_actual += actual
                                
                                # Project if incomplete month
                                projected_actual = actual
                                if m['completeness'] < 1.0:
                                    projected_actual = actual  # Already projected above
                                
                                variance_pct = (projected_actual - budgeted) / budgeted * 100 if budgeted > 0 else 0
                                
                                if variance_pct <= 10:  # Within 10% = on budget
                                    categories_on_budget += 1
                                elif variance_pct > 10:
                                    categories_over += 1
                                    if variance_pct > 25:  # Significantly over
                                        over_budget_cats.append({
                                            'category': cat_name,
                                            'budgeted': budgeted,
                                            'actual': projected_actual,
                                            'variance_pct': variance_pct
                                        })
                                else:
                                    categories_under += 1
                        
                        total_cats = categories_on_budget + categories_over + categories_under
                        if total_cats > 0:
                            adherence_pct = (categories_on_budget + categories_under) / total_cats * 100
                            budget_scores.append((adherence_pct, m['completeness']))
                            
                            if over_budget_cats:
                                budget_insights.extend(over_budget_cats[:3])
            
            if budget_scores:
                total_weight = sum(w for _, w in budget_scores)
                avg_adherence = sum(s * w for s, w in budget_scores) / total_weight
            else:
                avg_adherence = 70  # Neutral if no budget
            
            factors['budget_adherence'] = {
                'value': round(avg_adherence, 1),
                'score': round(avg_adherence, 1),
                'weight': 0.25,
                'description': 'Staying within budget limits',
                'status': 'good' if avg_adherence >= 80 else 'fair' if avg_adherence >= 60 else 'poor',
                'has_budget': budget is not None
            }
            
            # 4. Commission Utilization (15%)
            commission_scores = []
            for m in months_data:
                if m['commission_income'] > 0 and m['completeness'] >= 0.5:
                    commission = m['commission_income']
                    invested = m['investments']
                    if commission > 0:
                        invest_ratio = invested / commission
                        util_score = 50 + (invest_ratio * 50)
                        commission_scores.append((min(100, util_score), m['completeness']))
            
            if commission_scores:
                total_weight = sum(w for _, w in commission_scores)
                avg_commission_util = sum(s * w for s, w in commission_scores) / total_weight
            else:
                avg_commission_util = 70
            
            factors['commission_utilization'] = {
                'value': round(avg_commission_util, 1),
                'score': round(avg_commission_util, 1),
                'weight': 0.15,
                'description': 'Commission used for investing',
                'status': 'good' if avg_commission_util >= 70 else 'fair' if avg_commission_util >= 50 else 'poor'
            }
            
            # 5. Spending Consistency (15%)
            recurring = [m['recurring_expenses'] for m in months_data if m['completeness'] >= 0.5]
            if len(recurring) >= 2:
                variability = np.std(recurring) / np.mean(recurring) if np.mean(recurring) > 0 else 0
                consistency_score = max(0, min(100, 100 - (variability * 150)))
            else:
                variability, consistency_score = 0, 50
            
            factors['spending_consistency'] = {
                'value': round(variability * 100, 1),
                'score': round(consistency_score, 1),
                'weight': 0.15,
                'description': 'Recurring expense stability',
                'status': 'good' if consistency_score >= 70 else 'fair' if consistency_score >= 40 else 'poor'
            }
            
            total_score = sum(f['score'] * f['weight'] for f in factors.values())
            complete_months = sum(1 for m in months_data if m['completeness'] >= 0.9)
            data_quality = "good" if complete_months >= 3 else "partial" if complete_months >= 2 else "limited"
            
            recommendations = self._generate_health_recommendations(factors, total_score, months_data, budget, budget_insights)
            
            total_base = sum(m['base_income'] for m in months_data)
            total_commission = sum(m['commission_income'] for m in months_data)
            total_other = sum(m['other_income'] for m in months_data)
            
            house_months = [m for m in months_data if m['in_house_event']]
            total_house_spending = sum(m['house_related'] for m in house_months)
            
            return {
                "score": round(total_score, 1),
                "grade": self._get_grade(total_score),
                "factors": factors,
                "recommendations": recommendations,
                "data_quality": data_quality,
                "months_analyzed": len(months_data),
                "period": "Trailing 3 months",
                "calculated_at": today.isoformat(),
                "budget_info": {
                    "has_active_budget": budget is not None,
                    "budget_name": budget['name'] if budget else None,
                    "total_budgeted": budget['total_budgeted'] if budget else 0,
                    "categories_tracked": len(budget['items']) if budget else 0
                },
                "income_breakdown": {
                    "base_salary": round(total_base, 2),
                    "commission": round(total_commission, 2),
                    "other": round(total_other, 2),
                    "note": "Commission variability is expected"
                },
                "life_events": {
                    "house_purchase": {
                        "active": any(m['in_house_event'] for m in months_data),
                        "house_related_spending": round(total_house_spending, 2)
                    }
                },
                "spending_breakdown": {
                    "recurring_monthly_avg": round(np.mean([m['recurring_expenses'] for m in months_data]), 2),
                    "one_time_total": round(sum(m['one_time_expenses'] for m in months_data), 2)
                },
                "note": "Budget-aware scoring with commission income support"
            }
            
        finally:
            session.close()
    
    def _get_grade(self, score):
        if score >= 90: return "A+"
        elif score >= 85: return "A"
        elif score >= 80: return "A-"
        elif score >= 75: return "B+"
        elif score >= 70: return "B"
        elif score >= 65: return "B-"
        elif score >= 60: return "C+"
        elif score >= 55: return "C"
        elif score >= 50: return "C-"
        elif score >= 45: return "D+"
        elif score >= 40: return "D"
        else: return "F"
    
    def _generate_health_recommendations(self, factors, total_score, months_data, budget, budget_insights):
        recommendations = []
        in_house_event = any(m['in_house_event'] for m in months_data)
        
        # Budget-specific recommendations
        budget_adherence = factors.get('budget_adherence', {})
        if budget and budget_adherence.get('status') == 'poor':
            recommendations.append({
                'priority': 'medium',
                'message': "📊 Several categories over budget. Review spending in Budget tab."
            })
        elif budget and budget_adherence.get('status') == 'good':
            recommendations.append({
                'priority': 'info',
                'message': "✅ Great job staying within your budget!"
            })
        
        # Specific over-budget categories
        if budget_insights:
            top_over = sorted(budget_insights, key=lambda x: x['variance_pct'], reverse=True)[:2]
            for item in top_over:
                recommendations.append({
                    'priority': 'medium',
                    'message': f"⚠️ {item['category']}: ${item['actual']:.0f} vs ${item['budgeted']:.0f} budget (+{item['variance_pct']:.0f}%)"
                })
        
        # Base coverage
        base_coverage = factors.get('base_coverage', {})
        if base_coverage.get('status') == 'good':
            recommendations.append({
                'priority': 'info',
                'message': "✅ Base salary covers recurring - commission is bonus!"
            })
        elif base_coverage.get('status') == 'poor':
            recommendations.append({
                'priority': 'medium',
                'message': "💰 Base salary doesn't cover recurring. Reduce fixed costs."
            })
        
        # Commission utilization
        commission_util = factors.get('commission_utilization', {})
        if commission_util.get('score', 0) >= 70:
            recommendations.append({
                'priority': 'info',
                'message': "🌟 Great job investing commission income!"
            })
        
        # House event
        if in_house_event:
            house_spending = sum(m['house_related'] for m in months_data if m['in_house_event'])
            if house_spending > 0:
                recommendations.append({
                    'priority': 'info',
                    'message': f"🏠 House costs: ${house_spending:,.0f} - expected to normalize."
                })
        
        # Savings rate
        savings = factors.get('savings_rate', {})
        if savings.get('value', 0) >= 30:
            recommendations.append({
                'priority': 'info',
                'message': f"💪 Excellent {savings.get('value', 0):.0f}% savings rate!"
            })
        
        priority_order = {'high': 0, 'medium': 1, 'low': 2, 'info': 3}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 99))
        return recommendations[:6]
    
    def detect_spending_anomalies(self, user_id=1, lookback_days=90):
        """Detect anomalies with budget context."""
        session = get_session()
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=lookback_days)
            excluded_ids = self._get_excluded_category_ids(session)
            budget = self._get_active_budget(session, user_id)
            
            transactions = session.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.date >= start_date,
                Transaction.amount < 0
            ).all()
            
            if len(transactions) < 10:
                return {"anomalies": [], "message": "Insufficient data"}
            
            expenses = []
            for t in transactions:
                cat = session.query(Category).filter_by(id=t.category_id).first()
                cat_name = cat.name if cat else 'Uncategorized'
                if self._is_actual_spending(t, cat_name, excluded_ids):
                    life_event = self._get_life_event_context(t.date, cat_name)
                    budget_item = budget['items'].get(cat_name.lower()) if budget else None
                    expenses.append((t, cat_name, life_event, budget_item))
            
            if not expenses:
                return {"anomalies": [], "message": "No expenses after filtering"}
            
            anomalies = []
            seen = set()
            
            normal_expenses = [(t, c, e, b) for t, c, e, b in expenses if e != 'House purchase']
            house_expenses = [(t, c, e, b) for t, c, e, b in expenses if e == 'House purchase']
            
            if normal_expenses:
                amounts = [abs(t.amount) for t, _, _, _ in normal_expenses]
                mean, std = np.mean(amounts), np.std(amounts)
                p95 = np.percentile(amounts, 95) if len(amounts) > 5 else mean * 2
                
                for t, cat_name, _, budget_item in normal_expenses:
                    amt = abs(t.amount)
                    
                    # Check against budget if available
                    budget_context = None
                    if budget_item:
                        monthly_budget = budget_item['budgeted_amount']
                        if amt > monthly_budget * 0.5:  # Single transaction > 50% of monthly budget
                            budget_context = f"This is {amt/monthly_budget*100:.0f}% of your ${monthly_budget:.0f} monthly {cat_name} budget"
                    
                    if amt >= p95 and t.id not in seen:
                        seen.add(t.id)
                        anomalies.append({
                            'type': 'large_transaction',
                            'date': t.date.isoformat(),
                            'amount': round(amt, 2),
                            'description': (t.description[:40] + '...') if t.description and len(t.description) > 40 else t.description or 'Unknown',
                            'category': cat_name,
                            'severity': 'medium',
                            'message': f"${amt:,.2f} - top 5% spending",
                            'recommendation': f"Verify {cat_name} expense.",
                            'budget_context': budget_context,
                            'context': None
                        })
            
            for t, cat_name, event, _ in house_expenses:
                amt = abs(t.amount)
                if amt > 500 and t.id not in seen:
                    seen.add(t.id)
                    anomalies.append({
                        'type': 'house_related',
                        'date': t.date.isoformat(),
                        'amount': round(amt, 2),
                        'description': (t.description[:40] + '...') if t.description and len(t.description) > 40 else t.description or 'Unknown',
                        'category': cat_name,
                        'severity': 'low',
                        'message': f"${amt:,.2f} - House related",
                        'recommendation': "Expected house cost.",
                        'context': 'House purchase (Oct 2025)'
                    })
            
            severity_order = {'high': 0, 'medium': 1, 'low': 2}
            anomalies.sort(key=lambda x: (severity_order.get(x['severity'], 99), -x['amount']))
            
            return {
                "anomalies": anomalies[:12],
                "total_found": len(anomalies),
                "total_analyzed": len(expenses),
                "budget_integrated": budget is not None,
                "period": f"{lookback_days} days",
                "note": "Anomalies include budget context when available"
            }
        finally:
            session.close()
    
    def predict_monthly_spending(self, user_id=1, months_ahead=3):
        """Predict spending with budget comparison."""
        session = get_session()
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=365)
            excluded_ids = self._get_excluded_category_ids(session)
            budget = self._get_active_budget(session, user_id)
            
            transactions = session.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.date >= start_date,
                Transaction.amount < 0
            ).all()
            
            if len(transactions) < 20:
                return {"predictions": [], "message": "Insufficient data"}
            
            monthly_recurring = defaultdict(float)
            monthly_one_time = defaultdict(float)
            monthly_investments = defaultdict(float)
            
            for t in transactions:
                cat = session.query(Category).filter_by(id=t.category_id).first()
                cat_name = cat.name if cat else 'Uncategorized'
                month_key = t.date.strftime('%Y-%m')
                
                if self._is_investment_transfer(t):
                    monthly_investments[month_key] += abs(t.amount)
                    continue
                
                if self._is_actual_spending(t, cat_name, excluded_ids):
                    if cat_name in self.ONE_TIME_CATEGORIES:
                        monthly_one_time[month_key] += abs(t.amount)
                    else:
                        monthly_recurring[month_key] += abs(t.amount)
            
            if len(monthly_recurring) < 3:
                return {"predictions": [], "message": "Need 3+ months"}
            
            sorted_months = sorted(monthly_recurring.keys())
            recurring_amounts = [monthly_recurring[m] for m in sorted_months]
            
            median_recurring = np.median(recurring_amounts)
            filtered_amounts = [a for a in recurring_amounts if a < median_recurring * 3]
            if len(filtered_amounts) < 3:
                filtered_amounts = recurring_amounts
            
            avg_recurring = np.mean(filtered_amounts[-3:]) if len(filtered_amounts) >= 3 else np.mean(filtered_amounts)
            std_recurring = np.std(filtered_amounts) if len(filtered_amounts) > 1 else avg_recurring * 0.2
            
            # Compare to budget
            budget_comparison = None
            if budget:
                total_budgeted = budget['total_budgeted']
                budget_comparison = {
                    'total_budgeted': total_budgeted,
                    'predicted_vs_budget': round((avg_recurring / total_budgeted - 1) * 100, 1) if total_budgeted > 0 else 0,
                    'status': 'on_track' if avg_recurring <= total_budgeted * 1.1 else 'over_budget'
                }
            
            predictions = []
            for i in range(1, months_ahead + 1):
                future = date.today() + timedelta(days=30 * i)
                predictions.append({
                    'month': future.strftime('%Y-%m'),
                    'predicted_recurring': round(avg_recurring, 2),
                    'confidence_interval': {
                        'lower': round(max(0, avg_recurring - 1.645 * std_recurring), 2),
                        'upper': round(avg_recurring + 1.645 * std_recurring, 2)
                    },
                    'confidence_level': 90,
                    'trend': 'Stable',
                    'budget_amount': budget['total_budgeted'] if budget else None,
                    'note': 'Based on recurring expenses'
                })
            
            return {
                "predictions": predictions,
                "historical_months": len(recurring_amounts),
                "avg_recurring": round(avg_recurring, 2),
                "median_recurring": round(median_recurring, 2),
                "avg_one_time": round(np.mean(list(monthly_one_time.values())) if monthly_one_time else 0, 2),
                "total_investments_tracked": round(sum(monthly_investments.values()), 2),
                "budget_comparison": budget_comparison,
                "note": "Predictions compared against your active budget"
            }
        finally:
            session.close()
    
    def get_spending_insights(self, user_id=1):
        """Generate insights with budget integration."""
        session = get_session()
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=90)
            excluded_ids = self._get_excluded_category_ids(session)
            budget = self._get_active_budget(session, user_id)
            
            transactions = session.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.date >= start_date
            ).all()
            
            if not transactions:
                return {"insights": [], "message": "No data"}
            
            base_income = 0
            commission_income = 0
            other_income = 0
            investments = []
            recurring_expenses = []
            house_expenses = []
            
            for t in transactions:
                cat = session.query(Category).filter_by(id=t.category_id).first()
                cat_name = cat.name if cat else 'Uncategorized'
                
                if t.amount > 0:
                    if self._is_paycheck(t):
                        if self._classify_income(t.amount) == 'base':
                            base_income += t.amount
                        else:
                            commission_income += t.amount
                    else:
                        other_income += t.amount
                elif self._is_investment_transfer(t):
                    investments.append((t, cat_name))
                elif self._is_actual_spending(t, cat_name, excluded_ids):
                    life_event = self._get_life_event_context(t.date, cat_name)
                    if life_event == 'House purchase':
                        house_expenses.append((t, cat_name))
                    else:
                        recurring_expenses.append((t, cat_name))
            
            insights = []
            total_income = base_income + commission_income + other_income
            
            # Budget vs Actual insight
            if budget:
                cat_totals = defaultdict(float)
                for t, cat_name in recurring_expenses:
                    cat_totals[cat_name] += abs(t.amount)
                
                over_budget_cats = []
                under_budget_cats = []
                
                for cat_name, actual in cat_totals.items():
                    budget_item = budget['items'].get(cat_name.lower())
                    if budget_item:
                        budgeted = budget_item['budgeted_amount'] * 3  # 3 months
                        variance_pct = (actual - budgeted) / budgeted * 100 if budgeted > 0 else 0
                        if variance_pct > 20:
                            over_budget_cats.append((cat_name, actual, budgeted, variance_pct))
                        elif variance_pct < -20:
                            under_budget_cats.append((cat_name, actual, budgeted, abs(variance_pct)))
                
                if over_budget_cats:
                    top_over = sorted(over_budget_cats, key=lambda x: x[3], reverse=True)[0]
                    insights.append({
                        'type': 'over_budget', 'priority': 'medium',
                        'title': f"⚠️ {top_over[0]} over budget by {top_over[3]:.0f}%",
                        'description': f"Spent ${top_over[1]:,.0f} vs ${top_over[2]:,.0f} budgeted",
                        'recommendation': f"Review {top_over[0]} spending or adjust budget."
                    })
                
                if under_budget_cats:
                    top_under = sorted(under_budget_cats, key=lambda x: x[3], reverse=True)[0]
                    insights.append({
                        'type': 'under_budget', 'priority': 'info',
                        'title': f"✅ {top_under[0]} under budget by {top_under[3]:.0f}%",
                        'description': f"Spent ${top_under[1]:,.0f} vs ${top_under[2]:,.0f} budgeted",
                        'recommendation': "Great discipline! Consider reallocating savings."
                    })
            
            # Commission income insight
            if commission_income > 0:
                commission_pct = commission_income / total_income * 100 if total_income > 0 else 0
                insights.append({
                    'type': 'income_breakdown', 'priority': 'info',
                    'title': f"💼 Commission: ${commission_income:,.0f} ({commission_pct:.0f}%)",
                    'description': f"Base: ${base_income:,.0f}",
                    'recommendation': "Commission variability is normal."
                })
            
            # House purchase insight
            if house_expenses:
                house_total = sum(abs(t.amount) for t, _ in house_expenses)
                insights.append({
                    'type': 'life_event', 'priority': 'info',
                    'title': f"🏠 House costs: ${house_total:,.0f}",
                    'description': "Setup expenses from Oct 2025",
                    'recommendation': "Expected - will normalize."
                })
            
            # Investment tracking
            total_invested = sum(abs(t.amount) for t, _ in investments)
            if total_invested > 100:
                # Compare to budget savings goal if exists
                savings_budget = budget['items'].get('savings') if budget else None
                savings_note = ""
                if savings_budget:
                    savings_goal = savings_budget['budgeted_amount'] * 3
                    if total_invested >= savings_goal:
                        savings_note = f" (exceeds ${savings_goal:,.0f} goal!)"
                
                insights.append({
                    'type': 'investments', 'priority': 'info',
                    'title': f"💰 ${total_invested:,.0f} invested{savings_note}",
                    'description': f"{len(investments)} transfers",
                    'recommendation': "Great investing habit!"
                })
            
            # Base salary coverage
            total_recurring = sum(abs(t.amount) for t, _ in recurring_expenses)
            if base_income > 0 and total_recurring > 0:
                coverage = base_income / total_recurring * 100
                if coverage >= 100:
                    insights.append({
                        'type': 'base_coverage', 'priority': 'info',
                        'title': f"✅ Base covers {coverage:.0f}% of recurring",
                        'description': "Commission is pure bonus!",
                        'recommendation': "Excellent - invest commission."
                    })
            
            priority_order = {'high': 0, 'medium': 1, 'low': 2, 'info': 3}
            insights.sort(key=lambda x: priority_order.get(x.get('priority', 'info'), 99))
            
            total_house = sum(abs(t.amount) for t, _ in house_expenses)
            
            # Calculate category totals for summary
            cat_totals = defaultdict(float)
            for t, cat_name in recurring_expenses:
                cat_totals[cat_name] += abs(t.amount)
            
            return {
                "insights": insights[:8],
                "total_insights": len(insights),
                "period": "90 days",
                "budget_integrated": budget is not None,
                "budget_name": budget['name'] if budget else None,
                "summary": {
                    "base_income": round(base_income, 2),
                    "commission_income": round(commission_income, 2),
                    "total_income": round(total_income, 2),
                    "recurring_expenses": round(total_recurring, 2),
                    "house_related_expenses": round(total_house, 2),
                    "total_invested": round(total_invested, 2),
                    "categories": len(cat_totals)
                },
                "life_events": ["House purchase (Oct 2025)"] if house_expenses else [],
                "note": "Insights compare actual spending to your budget"
            }
        finally:
            session.close()
    
    def get_budget_analysis(self, user_id=1):
        """Get detailed budget vs actual analysis."""
        session = get_session()
        try:
            budget = self._get_active_budget(session, user_id)
            if not budget:
                return {"error": "No active budget found", "has_budget": False}
            
            # Get current month spending
            today = date.today()
            month_start = date(today.year, today.month, 1)
            excluded_ids = self._get_excluded_category_ids(session)
            
            transactions = session.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.date >= month_start,
                Transaction.amount < 0
            ).all()
            
            # Calculate actual spending by category
            category_spending = defaultdict(float)
            for t in transactions:
                cat = session.query(Category).filter_by(id=t.category_id).first()
                cat_name = cat.name if cat else 'Uncategorized'
                if self._is_actual_spending(t, cat_name, excluded_ids):
                    category_spending[cat_name] += abs(t.amount)
            
            # Compare to budget
            analysis = []
            total_budgeted = 0
            total_actual = 0
            
            for cat_name_lower, budget_item in budget['items'].items():
                cat_name = budget_item['category_name']
                budgeted = budget_item['budgeted_amount']
                actual = category_spending.get(cat_name, 0)
                
                total_budgeted += budgeted
                total_actual += actual
                
                # Project to end of month
                days_passed = today.day
                days_in_month = monthrange(today.year, today.month)[1]
                projected = actual / days_passed * days_in_month if days_passed > 0 else actual
                
                variance = actual - budgeted
                variance_pct = (variance / budgeted * 100) if budgeted > 0 else 0
                projected_variance = projected - budgeted
                projected_variance_pct = (projected_variance / budgeted * 100) if budgeted > 0 else 0
                
                status = 'on_track'
                if projected_variance_pct > 20:
                    status = 'over_budget'
                elif projected_variance_pct > 10:
                    status = 'at_risk'
                elif projected_variance_pct < -20:
                    status = 'under_budget'
                
                analysis.append({
                    'category': cat_name,
                    'budgeted': round(budgeted, 2),
                    'actual': round(actual, 2),
                    'projected': round(projected, 2),
                    'variance': round(variance, 2),
                    'variance_pct': round(variance_pct, 1),
                    'projected_variance': round(projected_variance, 2),
                    'projected_variance_pct': round(projected_variance_pct, 1),
                    'status': status
                })
            
            # Sort by variance (most over budget first)
            analysis.sort(key=lambda x: x['projected_variance_pct'], reverse=True)
            
            return {
                "has_budget": True,
                "budget_name": budget['name'],
                "period": today.strftime('%Y-%m'),
                "days_in_month": days_in_month,
                "days_passed": days_passed,
                "completion_pct": round(days_passed / days_in_month * 100, 1),
                "totals": {
                    "budgeted": round(total_budgeted, 2),
                    "actual": round(total_actual, 2),
                    "projected": round(total_actual / days_passed * days_in_month if days_passed > 0 else total_actual, 2),
                    "remaining": round(total_budgeted - total_actual, 2)
                },
                "categories": analysis,
                "summary": {
                    "on_track": sum(1 for a in analysis if a['status'] == 'on_track'),
                    "at_risk": sum(1 for a in analysis if a['status'] == 'at_risk'),
                    "over_budget": sum(1 for a in analysis if a['status'] == 'over_budget'),
                    "under_budget": sum(1 for a in analysis if a['status'] == 'under_budget')
                }
            }
        finally:
            session.close()


    def get_category_trends(self, user_id=1, months=3):
        """Analyze category spending trends over time."""
        session = get_session()
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=months * 31)
            excluded_ids = self._get_excluded_category_ids(session)
            
            transactions = session.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.date >= start_date,
                Transaction.amount < 0
            ).all()
            
            if len(transactions) < 10:
                return {"trends": [], "message": "Insufficient data"}
            
            # Group spending by month and category
            monthly_category = defaultdict(lambda: defaultdict(float))
            
            for t in transactions:
                cat = session.query(Category).filter_by(id=t.category_id).first()
                cat_name = cat.name if cat else 'Uncategorized'
                
                if self._is_actual_spending(t, cat_name, excluded_ids):
                    month_key = t.date.strftime('%Y-%m')
                    monthly_category[month_key][cat_name] += abs(t.amount)
            
            if len(monthly_category) < 2:
                return {"trends": [], "message": "Need at least 2 months of data"}
            
            # Sort months chronologically
            sorted_months = sorted(monthly_category.keys())
            
            # Calculate trends for each category
            trends = []
            all_categories = set()
            for month_data in monthly_category.values():
                all_categories.update(month_data.keys())
            
            for cat_name in all_categories:
                amounts = [monthly_category[m].get(cat_name, 0) for m in sorted_months]
                
                # Skip categories with minimal spending
                if max(amounts) < 50:
                    continue
                
                # Calculate month-over-month change
                recent = amounts[-1] if amounts else 0
                previous = amounts[-2] if len(amounts) >= 2 else 0
                
                if previous > 0:
                    change_pct = ((recent - previous) / previous) * 100
                elif recent > 0:
                    change_pct = 100  # New spending
                else:
                    change_pct = 0
                
                # Calculate average and trend direction
                avg_amount = np.mean([a for a in amounts if a > 0]) if any(amounts) else 0
                
                # Determine trend using simple linear regression
                if len(amounts) >= 2:
                    x = np.arange(len(amounts))
                    slope = np.polyfit(x, amounts, 1)[0]
                    
                    if slope > avg_amount * 0.1:
                        trend_direction = 'increasing'
                        trend_icon = '📈'
                    elif slope < -avg_amount * 0.1:
                        trend_direction = 'decreasing'
                        trend_icon = '📉'
                    else:
                        trend_direction = 'stable'
                        trend_icon = '➡️'
                else:
                    trend_direction = 'stable'
                    trend_icon = '➡️'
                    slope = 0
                
                trends.append({
                    'category': cat_name,
                    'current_month': round(recent, 2),
                    'previous_month': round(previous, 2),
                    'change_amount': round(recent - previous, 2),
                    'change_pct': round(change_pct, 1),
                    'average': round(avg_amount, 2),
                    'trend_direction': trend_direction,
                    'trend_icon': trend_icon,
                    'monthly_amounts': {m: round(monthly_category[m].get(cat_name, 0), 2) for m in sorted_months},
                    'slope': round(slope, 2)
                })
            
            # Sort by absolute change percentage (biggest movers first)
            trends.sort(key=lambda x: abs(x['change_pct']), reverse=True)
            
            # Separate into increasing, decreasing, stable
            increasing = [t for t in trends if t['trend_direction'] == 'increasing']
            decreasing = [t for t in trends if t['trend_direction'] == 'decreasing']
            stable = [t for t in trends if t['trend_direction'] == 'stable']
            
            # Generate summary insights
            insights = []
            
            if increasing:
                top_increase = increasing[0]
                insights.append({
                    'type': 'top_increase',
                    'message': f"📈 {top_increase['category']} up {top_increase['change_pct']:.0f}% (${top_increase['previous_month']:.0f} → ${top_increase['current_month']:.0f})"
                })
            
            if decreasing:
                top_decrease = decreasing[0]
                insights.append({
                    'type': 'top_decrease',
                    'message': f"📉 {top_decrease['category']} down {abs(top_decrease['change_pct']):.0f}% (${top_decrease['previous_month']:.0f} → ${top_decrease['current_month']:.0f})"
                })
            
            # Total spending trend
            total_by_month = {m: sum(monthly_category[m].values()) for m in sorted_months}
            total_recent = total_by_month[sorted_months[-1]]
            total_previous = total_by_month[sorted_months[-2]] if len(sorted_months) >= 2 else 0
            
            if total_previous > 0:
                total_change_pct = ((total_recent - total_previous) / total_previous) * 100
                insights.append({
                    'type': 'total_trend',
                    'message': f"{'📈' if total_change_pct > 0 else '📉'} Total spending {'up' if total_change_pct > 0 else 'down'} {abs(total_change_pct):.0f}% month-over-month"
                })
            
            return {
                "trends": trends[:15],  # Top 15 categories
                "total_categories": len(trends),
                "months_analyzed": len(sorted_months),
                "period": f"{sorted_months[0]} to {sorted_months[-1]}",
                "summary": {
                    "increasing": len(increasing),
                    "decreasing": len(decreasing),
                    "stable": len(stable)
                },
                "insights": insights,
                "total_by_month": {m: round(v, 2) for m, v in total_by_month.items()}
            }
        finally:
            session.close()


_analytics = None

def get_analytics():
    global _analytics
    if _analytics is None:
        _analytics = AdvancedAnalytics()
    return _analytics
