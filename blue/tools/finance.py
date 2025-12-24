"""
Blue Robot Finance & Budget Tracker
====================================
Track expenses, income, budgets, and financial goals with comprehensive analytics.
"""

# Future imports
from __future__ import annotations

# Standard library
import datetime
import json
import os
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ================================================================================
# CONFIGURATION
# ================================================================================

FINANCE_DB = os.environ.get("BLUE_FINANCE_DB", os.path.join("data", "finance.db"))


class TransactionType(Enum):
    """Type of financial transaction"""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class TransactionCategory(Enum):
    """Categories for transactions"""
    # Income categories
    SALARY = "salary"
    FREELANCE = "freelance"
    INVESTMENT = "investment"
    GIFT = "gift"
    OTHER_INCOME = "other_income"

    # Expense categories
    FOOD = "food"
    TRANSPORTATION = "transportation"
    HOUSING = "housing"
    UTILITIES = "utilities"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    SUBSCRIPTION = "subscription"
    DEBT = "debt"
    SAVINGS = "savings"
    OTHER_EXPENSE = "other_expense"


class BudgetPeriod(Enum):
    """Budget period types"""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class Transaction:
    """Represents a financial transaction"""
    id: str
    type: TransactionType
    category: TransactionCategory
    amount: float
    description: str
    date: float
    account: str
    tags: List[str]
    created_at: float
    recurring: bool = False
    recurring_period: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "category": self.category.value,
            "amount": self.amount,
            "description": self.description,
            "date": datetime.datetime.fromtimestamp(self.date).isoformat(),
            "date_human": datetime.datetime.fromtimestamp(self.date).strftime("%b %d, %Y"),
            "account": self.account,
            "tags": self.tags,
            "recurring": self.recurring,
            "recurring_period": self.recurring_period,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat()
        }


@dataclass
class Budget:
    """Represents a budget for a category"""
    id: str
    category: TransactionCategory
    amount: float
    period: BudgetPeriod
    start_date: float
    active: bool
    created_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "amount": self.amount,
            "period": self.period.value,
            "start_date": datetime.datetime.fromtimestamp(self.start_date).isoformat(),
            "active": self.active,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat()
        }


@dataclass
class FinancialGoal:
    """Represents a financial goal"""
    id: str
    name: str
    target_amount: float
    current_amount: float
    deadline: Optional[float]
    category: str
    created_at: float
    completed: bool = False
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        progress = (self.current_amount / self.target_amount * 100) if self.target_amount > 0 else 0
        result = {
            "id": self.id,
            "name": self.name,
            "target_amount": self.target_amount,
            "current_amount": self.current_amount,
            "remaining": self.target_amount - self.current_amount,
            "progress_percent": round(progress, 2),
            "category": self.category,
            "completed": self.completed,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat()
        }
        if self.deadline:
            result["deadline"] = datetime.datetime.fromtimestamp(self.deadline).isoformat()
            result["deadline_human"] = datetime.datetime.fromtimestamp(self.deadline).strftime("%b %d, %Y")
        if self.completed_at:
            result["completed_at"] = datetime.datetime.fromtimestamp(self.completed_at).isoformat()
        return result


# ================================================================================
# FINANCE MANAGER
# ================================================================================

class FinanceManager:
    """Manages financial tracking, budgets, and goals"""

    def __init__(self, db_path: str = FINANCE_DB):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT NOT NULL,
                date REAL NOT NULL,
                account TEXT NOT NULL,
                tags TEXT,
                created_at REAL NOT NULL,
                recurring INTEGER DEFAULT 0,
                recurring_period TEXT
            )
        """)

        # Budgets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                period TEXT NOT NULL,
                start_date REAL NOT NULL,
                active INTEGER DEFAULT 1,
                created_at REAL NOT NULL
            )
        """)

        # Financial goals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_goals (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                deadline REAL,
                category TEXT NOT NULL,
                created_at REAL NOT NULL,
                completed INTEGER DEFAULT 0,
                completed_at REAL
            )
        """)

        # Accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                name TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                balance REAL DEFAULT 0,
                created_at REAL NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    # ==================== TRANSACTIONS ====================

    def add_transaction(self, type: str, category: str, amount: float,
                       description: str, date: float = None, account: str = "default",
                       tags: List[str] = None, recurring: bool = False,
                       recurring_period: str = None) -> Transaction:
        """Add a new transaction"""
        transaction_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()
        transaction_date = date if date else now

        try:
            type_enum = TransactionType(type.lower())
            category_enum = TransactionCategory(category.lower())
        except ValueError as e:
            raise ValueError(f"Invalid type or category: {e}")

        transaction = Transaction(
            id=transaction_id,
            type=type_enum,
            category=category_enum,
            amount=abs(amount),
            description=description,
            date=transaction_date,
            account=account,
            tags=tags or [],
            created_at=now,
            recurring=recurring,
            recurring_period=recurring_period
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (id, type, category, amount, description, date, account, tags, created_at, recurring, recurring_period)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (transaction.id, transaction.type.value, transaction.category.value,
              transaction.amount, transaction.description, transaction.date,
              transaction.account, json.dumps(transaction.tags), transaction.created_at,
              1 if recurring else 0, recurring_period))
        conn.commit()
        conn.close()

        # Update account balance
        self._update_account_balance(account, amount if type_enum == TransactionType.INCOME else -amount)

        return transaction

    def get_transactions(self, start_date: float = None, end_date: float = None,
                        type: str = None, category: str = None,
                        account: str = None, limit: int = 50) -> List[Transaction]:
        """Get transactions with optional filters"""
        conn = self._get_conn()
        cursor = conn.cursor()

        sql = "SELECT * FROM transactions WHERE 1=1"
        params = []

        if start_date:
            sql += " AND date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date <= ?"
            params.append(end_date)
        if type:
            sql += " AND type = ?"
            params.append(type.lower())
        if category:
            sql += " AND category = ?"
            params.append(category.lower())
        if account:
            sql += " AND account = ?"
            params.append(account)

        sql += " ORDER BY date DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            Transaction(
                id=row[0], type=TransactionType(row[1]), category=TransactionCategory(row[2]),
                amount=row[3], description=row[4], date=row[5], account=row[6],
                tags=json.loads(row[7] or "[]"), created_at=row[8],
                recurring=bool(row[9]), recurring_period=row[10]
            )
            for row in rows
        ]

    def delete_transaction(self, transaction_id: str) -> bool:
        """Delete a transaction"""
        # Get transaction to reverse account balance
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT type, amount, account FROM transactions WHERE id = ?", (transaction_id,))
        row = cursor.fetchone()

        if row:
            type_val, amount, account = row
            cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()

            # Reverse account balance
            if deleted:
                reverse_amount = -amount if type_val == "income" else amount
                self._update_account_balance(account, reverse_amount)

            return deleted

        conn.close()
        return False

    def get_spending_by_category(self, start_date: float, end_date: float) -> Dict[str, float]:
        """Get spending breakdown by category"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category, SUM(amount)
            FROM transactions
            WHERE type = 'expense' AND date >= ? AND date <= ?
            GROUP BY category
        """, (start_date, end_date))

        result = {}
        for row in cursor.fetchall():
            result[row[0]] = row[1]

        conn.close()
        return result

    def get_income_summary(self, start_date: float, end_date: float) -> Dict[str, Any]:
        """Get income summary for period"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT SUM(amount), COUNT(*)
            FROM transactions
            WHERE type = 'income' AND date >= ? AND date <= ?
        """, (start_date, end_date))

        row = cursor.fetchone()
        total_income = row[0] or 0
        count = row[1]

        cursor.execute("""
            SELECT SUM(amount)
            FROM transactions
            WHERE type = 'expense' AND date >= ? AND date <= ?
        """, (start_date, end_date))

        total_expenses = cursor.fetchone()[0] or 0
        conn.close()

        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_income": total_income - total_expenses,
            "transaction_count": count
        }

    # ==================== BUDGETS ====================

    def create_budget(self, category: str, amount: float, period: str = "monthly") -> Budget:
        """Create a budget for a category"""
        budget_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()

        try:
            category_enum = TransactionCategory(category.lower())
            period_enum = BudgetPeriod(period.lower())
        except ValueError as e:
            raise ValueError(f"Invalid category or period: {e}")

        budget = Budget(
            id=budget_id,
            category=category_enum,
            amount=amount,
            period=period_enum,
            start_date=now,
            active=True,
            created_at=now
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO budgets (id, category, amount, period, start_date, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (budget.id, budget.category.value, budget.amount, budget.period.value,
              budget.start_date, 1, budget.created_at))
        conn.commit()
        conn.close()

        return budget

    def get_budgets(self, active_only: bool = True) -> List[Budget]:
        """Get all budgets"""
        conn = self._get_conn()
        cursor = conn.cursor()

        sql = "SELECT * FROM budgets"
        if active_only:
            sql += " WHERE active = 1"

        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()

        return [
            Budget(
                id=row[0], category=TransactionCategory(row[1]),
                amount=row[2], period=BudgetPeriod(row[3]),
                start_date=row[4], active=bool(row[5]),
                created_at=row[6]
            )
            for row in rows
        ]

    def check_budget_status(self, budget: Budget) -> Dict[str, Any]:
        """Check current spending against budget"""
        # Calculate period start date
        now = datetime.datetime.now()

        if budget.period == BudgetPeriod.WEEKLY:
            start = now - datetime.timedelta(days=7)
        elif budget.period == BudgetPeriod.MONTHLY:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # YEARLY
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get spending for this category in period
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(amount)
            FROM transactions
            WHERE category = ? AND type = 'expense' AND date >= ?
        """, (budget.category.value, start.timestamp()))

        spent = cursor.fetchone()[0] or 0
        conn.close()

        remaining = budget.amount - spent
        percent_used = (spent / budget.amount * 100) if budget.amount > 0 else 0

        return {
            "budget_id": budget.id,
            "category": budget.category.value,
            "budget_amount": budget.amount,
            "spent": spent,
            "remaining": remaining,
            "percent_used": round(percent_used, 2),
            "over_budget": spent > budget.amount,
            "period": budget.period.value
        }

    # ==================== FINANCIAL GOALS ====================

    def create_goal(self, name: str, target_amount: float, deadline: float = None,
                   category: str = "savings") -> FinancialGoal:
        """Create a financial goal"""
        goal_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()

        goal = FinancialGoal(
            id=goal_id,
            name=name,
            target_amount=target_amount,
            current_amount=0,
            deadline=deadline,
            category=category,
            created_at=now
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO financial_goals (id, name, target_amount, current_amount, deadline, category, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (goal.id, goal.name, goal.target_amount, goal.current_amount,
              goal.deadline, goal.category, goal.created_at))
        conn.commit()
        conn.close()

        return goal

    def update_goal_progress(self, goal_id: str, amount: float) -> Optional[FinancialGoal]:
        """Add to goal progress"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM financial_goals WHERE id = ?", (goal_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        new_amount = row[3] + amount
        completed = new_amount >= row[2]
        completed_at = datetime.datetime.now().timestamp() if completed and not row[7] else row[8]

        cursor.execute("""
            UPDATE financial_goals
            SET current_amount = ?, completed = ?, completed_at = ?
            WHERE id = ?
        """, (new_amount, 1 if completed else 0, completed_at, goal_id))
        conn.commit()
        conn.close()

        return self.get_goal(goal_id)

    def get_goal(self, goal_id: str) -> Optional[FinancialGoal]:
        """Get a financial goal by ID"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM financial_goals WHERE id = ?", (goal_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return FinancialGoal(
                id=row[0], name=row[1], target_amount=row[2],
                current_amount=row[3], deadline=row[4], category=row[5],
                created_at=row[6], completed=bool(row[7]),
                completed_at=row[8]
            )
        return None

    def get_goals(self, active_only: bool = True) -> List[FinancialGoal]:
        """Get all financial goals"""
        conn = self._get_conn()
        cursor = conn.cursor()

        sql = "SELECT * FROM financial_goals"
        if active_only:
            sql += " WHERE completed = 0"
        sql += " ORDER BY created_at DESC"

        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()

        return [
            FinancialGoal(
                id=row[0], name=row[1], target_amount=row[2],
                current_amount=row[3], deadline=row[4], category=row[5],
                created_at=row[6], completed=bool(row[7]),
                completed_at=row[8]
            )
            for row in rows
        ]

    # ==================== ACCOUNTS ====================

    def _update_account_balance(self, account: str, amount: float):
        """Update account balance"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT balance FROM accounts WHERE name = ?", (account,))
        row = cursor.fetchone()

        if row:
            new_balance = row[0] + amount
            cursor.execute("UPDATE accounts SET balance = ? WHERE name = ?", (new_balance, account))
        else:
            cursor.execute("""
                INSERT INTO accounts (name, type, balance, created_at)
                VALUES (?, ?, ?, ?)
            """, (account, "default", amount, datetime.datetime.now().timestamp()))

        conn.commit()
        conn.close()

    def get_account_balance(self, account: str = "default") -> float:
        """Get account balance"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM accounts WHERE name = ?", (account,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0.0


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_finance_manager: Optional[FinanceManager] = None


def get_finance_manager() -> FinanceManager:
    """Get or create singleton finance manager instance"""
    global _finance_manager
    if _finance_manager is None:
        _finance_manager = FinanceManager()
    return _finance_manager


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def add_expense_cmd(category: str, amount: float, description: str,
                   date: str = None, account: str = "default") -> str:
    """Add an expense transaction"""
    manager = get_finance_manager()

    transaction_date = None
    if date:
        # Blue package
        from blue.tools.calendar import parse_datetime
        dt = parse_datetime(date)
        if dt:
            transaction_date = dt.timestamp()

    transaction = manager.add_transaction(
        type="expense",
        category=category,
        amount=amount,
        description=description,
        date=transaction_date,
        account=account
    )

    return json.dumps({
        "status": "success",
        "message": f"Expense of ${amount:.2f} for {category} recorded",
        "transaction": transaction.to_dict()
    })


def add_income_cmd(category: str, amount: float, description: str,
                  date: str = None, account: str = "default") -> str:
    """Add an income transaction"""
    manager = get_finance_manager()

    transaction_date = None
    if date:
        # Blue package
        from blue.tools.calendar import parse_datetime
        dt = parse_datetime(date)
        if dt:
            transaction_date = dt.timestamp()

    transaction = manager.add_transaction(
        type="income",
        category=category,
        amount=amount,
        description=description,
        date=transaction_date,
        account=account
    )

    return json.dumps({
        "status": "success",
        "message": f"Income of ${amount:.2f} from {category} recorded",
        "transaction": transaction.to_dict()
    })


def get_transactions_cmd(days: int = 30, type: str = None, category: str = None) -> str:
    """Get recent transactions"""
    manager = get_finance_manager()

    end_date = datetime.datetime.now().timestamp()
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()

    transactions = manager.get_transactions(
        start_date=start_date,
        end_date=end_date,
        type=type,
        category=category
    )

    return json.dumps({
        "status": "success",
        "count": len(transactions),
        "transactions": [t.to_dict() for t in transactions]
    })


def create_budget_cmd(category: str, amount: float, period: str = "monthly") -> str:
    """Create a budget"""
    manager = get_finance_manager()

    budget = manager.create_budget(category, amount, period)

    return json.dumps({
        "status": "success",
        "message": f"Budget of ${amount:.2f} for {category} created ({period})",
        "budget": budget.to_dict()
    })


def check_budgets_cmd() -> str:
    """Check all budget statuses"""
    manager = get_finance_manager()

    budgets = manager.get_budgets(active_only=True)
    statuses = [manager.check_budget_status(budget) for budget in budgets]

    return json.dumps({
        "status": "success",
        "count": len(statuses),
        "budgets": statuses
    })


def create_financial_goal_cmd(name: str, target_amount: float, deadline: str = None) -> str:
    """Create a financial goal"""
    manager = get_finance_manager()

    deadline_timestamp = None
    if deadline:
        # Blue package
        from blue.tools.calendar import parse_datetime
        dt = parse_datetime(deadline)
        if dt:
            deadline_timestamp = dt.timestamp()

    goal = manager.create_goal(name, target_amount, deadline_timestamp)

    return json.dumps({
        "status": "success",
        "message": f"Financial goal '{name}' created with target of ${target_amount:.2f}",
        "goal": goal.to_dict()
    })


def update_goal_cmd(goal_id: str, amount: float) -> str:
    """Add progress to a financial goal"""
    manager = get_finance_manager()

    goal = manager.update_goal_progress(goal_id, amount)

    if goal:
        return json.dumps({
            "status": "success",
            "message": f"Added ${amount:.2f} to goal '{goal.name}'",
            "goal": goal.to_dict()
        })
    else:
        return json.dumps({
            "status": "error",
            "error": f"Goal not found: {goal_id}"
        })


def get_financial_summary_cmd(days: int = 30) -> str:
    """Get financial summary for period"""
    manager = get_finance_manager()

    end_date = datetime.datetime.now().timestamp()
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()

    summary = manager.get_income_summary(start_date, end_date)
    spending = manager.get_spending_by_category(start_date, end_date)

    return json.dumps({
        "status": "success",
        "period_days": days,
        "summary": summary,
        "spending_by_category": spending
    })


def get_balance_cmd(account: str = "default") -> str:
    """Get account balance"""
    manager = get_finance_manager()
    balance = manager.get_account_balance(account)

    return json.dumps({
        "status": "success",
        "account": account,
        "balance": balance
    })


__all__ = [
    'FinanceManager',
    'Transaction',
    'Budget',
    'FinancialGoal',
    'TransactionType',
    'TransactionCategory',
    'BudgetPeriod',
    'get_finance_manager',
    'add_expense_cmd',
    'add_income_cmd',
    'get_transactions_cmd',
    'create_budget_cmd',
    'check_budgets_cmd',
    'create_financial_goal_cmd',
    'update_goal_cmd',
    'get_financial_summary_cmd',
    'get_balance_cmd',
]
