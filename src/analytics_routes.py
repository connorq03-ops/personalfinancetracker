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
