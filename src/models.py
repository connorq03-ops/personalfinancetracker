"""
SQLAlchemy models for Personal Finance Tracker.
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class User(Base):
    """User model for multi-user support."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, default='Default User')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    categories = relationship('Category', back_populates='user', cascade='all, delete-orphan')
    transactions = relationship('Transaction', back_populates='user', cascade='all, delete-orphan')
    budgets = relationship('Budget', back_populates='user', cascade='all, delete-orphan')


class Category(Base):
    """Category for organizing transactions."""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    group = Column(String(100), nullable=False, default='Uncategorized')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship('User', back_populates='categories')
    transactions = relationship('Transaction', back_populates='category')
    budget_items = relationship('BudgetItem', back_populates='category')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'group': self.group
        }


class Transaction(Base):
    """Financial transaction record."""
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    date = Column(Date, nullable=False)
    description = Column(String(500), nullable=False)
    amount = Column(Float, nullable=False)  # Negative = expense, Positive = income
    source = Column(String(100))  # Bank name
    raw_category = Column(String(100))  # Original category from bank
    is_recurring = Column(Boolean, default=False)  # User-marked recurring transaction
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship('User', back_populates='transactions')
    category = relationship('Category', back_populates='transactions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'amount': self.amount,
            'source': self.source,
            'category': self.category.to_dict() if self.category else None
        }


class Budget(Base):
    """Budget for tracking spending goals."""
    __tablename__ = 'budgets'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(100), nullable=False)
    period_type = Column(String(20), default='monthly')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship('User', back_populates='budgets')
    items = relationship('BudgetItem', back_populates='budget', cascade='all, delete-orphan')


class BudgetItem(Base):
    """Individual budget line item."""
    __tablename__ = 'budget_items'
    
    id = Column(Integer, primary_key=True)
    budget_id = Column(Integer, ForeignKey('budgets.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    budgeted_amount = Column(Float, nullable=False)
    period = Column(String(7))  # Format: "2025-01"
    
    budget = relationship('Budget', back_populates='items')
    category = relationship('Category', back_populates='budget_items')


# Database initialization
_engine = None
_Session = None


def get_engine(db_path='finances.db'):
    """Get or create database engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(f'sqlite:///{db_path}', echo=False)
    return _engine


def get_session():
    """Get a new database session."""
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=get_engine())
    return _Session()


def init_db(db_path='finances.db'):
    """Initialize database with tables and default data."""
    global _engine, _Session
    _engine = create_engine(f'sqlite:///{db_path}', echo=False)
    _Session = sessionmaker(bind=_engine)
    
    Base.metadata.create_all(_engine)
    
    session = get_session()
    
    # Create default user if not exists
    user = session.query(User).first()
    if not user:
        user = User(name='Default User')
        session.add(user)
        session.commit()
        
        # Add default categories
        default_categories = [
            ('Groceries', 'Food'),
            ('Eating Out', 'Food'),
            ('Coffee', 'Food'),
            ('Gas', 'Transportation'),
            ('Uber/Lyft', 'Transportation'),
            ('Parking', 'Transportation'),
            ('Rent', 'Housing'),
            ('Utilities', 'Housing'),
            ('Entertainment', 'Entertainment'),
            ('Subscriptions', 'Entertainment'),
            ('Shopping', 'Shopping'),
            ('Income', 'Income'),
            ('Investments', 'Financial'),
            ('Credit Card Payment', 'Financial'),
            ('Transfer', 'Financial'),
            ('Healthcare', 'Health'),
            ('Uncategorized', 'Other'),
        ]
        
        for name, group in default_categories:
            session.add(Category(name=name, group=group, user_id=user.id))
        
        session.commit()
    
    session.close()
    return _engine


if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")
