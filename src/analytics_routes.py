"""
Analytics Routes - Flask blueprint for Advanced Analytics API
"""

from flask import Blueprint, jsonify, request
from advanced_analytics import get_analytics

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


@analytics_bp.route('/financial-health', methods=['GET'])
def get_financial_health():
    """Get comprehensive financial health score."""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        analytics = get_analytics()
        data = analytics.get_financial_health_score(user_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/anomalies', methods=['GET'])
def get_anomalies():
    """Detect spending anomalies."""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        lookback_days = request.args.get('lookback_days', 90, type=int)
        analytics = get_analytics()
        data = analytics.detect_spending_anomalies(user_id, lookback_days)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/predictions', methods=['GET'])
def get_predictions():
    """Get spending predictions."""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        months_ahead = request.args.get('months_ahead', 3, type=int)
        analytics = get_analytics()
        data = analytics.predict_monthly_spending(user_id, months_ahead)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/insights', methods=['GET'])
def get_insights():
    """Get spending insights."""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        analytics = get_analytics()
        data = analytics.get_spending_insights(user_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/dashboard', methods=['GET'])
def get_analytics_dashboard():
    """Get all analytics data for the dashboard."""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        analytics = get_analytics()
        
        return jsonify({
            'success': True,
            'data': {
                'financial_health': analytics.get_financial_health_score(user_id),
                'anomalies': analytics.detect_spending_anomalies(user_id),
                'predictions': analytics.predict_monthly_spending(user_id),
                'insights': analytics.get_spending_insights(user_id)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/budget-analysis', methods=['GET'])
def get_budget_analysis():
    """Get detailed budget vs actual analysis."""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        analytics = get_analytics()
        data = analytics.get_budget_analysis(user_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/category-trends', methods=['GET'])
def get_category_trends():
    """Get category spending trends over time."""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        months = request.args.get('months', 3, type=int)
        analytics = get_analytics()
        data = analytics.get_category_trends(user_id, months)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/merchants', methods=['GET'])
def get_merchant_analysis():
    """Get top merchants by spending."""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        months = request.args.get('months', 3, type=int)
        analytics = get_analytics()
        data = analytics.get_merchant_analysis(user_id, months)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/spending-patterns', methods=['GET'])
def get_spending_patterns():
    """Get spending patterns by day of week and time of month."""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        months = request.args.get('months', 3, type=int)
        analytics = get_analytics()
        data = analytics.get_spending_patterns(user_id, months)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/category-breakdown', methods=['GET'])
def get_category_breakdown():
    """Get spending breakdown by category for pie chart."""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        analytics = get_analytics()
        data = analytics.get_category_breakdown(user_id, year, month)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/recurring', methods=['GET'])
def get_recurring_transactions():
    """Detect recurring transactions (subscriptions, bills)."""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        months = request.args.get('months', 6, type=int)
        analytics = get_analytics()
        data = analytics.detect_recurring_transactions(user_id, months)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
