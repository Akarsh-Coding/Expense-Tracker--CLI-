import os
from pathlib import Path
import matplotlib.pyplot as plt
import calendar
import datetime

# ──────────────────────────────────────────────────────────────────────────────
#  Data classes & constants
# ──────────────────────────────────────────────────────────────────────────────
class Expense:
    """Single expense record."""

    def __init__(self, name: str, category: str, amount: float):
        self.name = name
        self.category = category
        self.amount = amount

    def __repr__(self) -> str:
        return f"<Expense: {self.name}, {self.category}, ₹{self.amount:.2f}>"


# Category list with emojis
EXPENSE_CATEGORIES = [
    ("Food", "🍔"), ("Transport", "🚌"), ("Home", "🏠"), ("Utilities", "💡"),
    ("Groceries", "🛒"), ("Entertainment", "🎮"), ("Health", "💊"),
    ("Education", "📚"), ("Shopping", "🛍️"), ("Work", "💼"),
    ("Travel", "✈️"), ("Miscellaneous", "📦")
]

# ──────────────────────────────────────────────────────────────────────────────
#  Helper functions
# ──────────────────────────────────────────────────────────────────────────────
def green(txt: str) -> str:
    """Return green-coloured text for CLI highlighting."""
    return f"\033[92m{txt}\033[0m"


def month_label(date: datetime.date) -> str:
    """Return a label like '2025-06'."""
    return f"{date.year}-{date.month:02d}"


def expense_file_for(date: datetime.date) -> Path:
    """Path to this month's expenses CSV."""
    return Path(f"expenses_{month_label(date)}.csv")


def budget_file_for(date: datetime.date) -> Path:
    """Path to this month's budget TXT."""
    return Path(f"budget_{month_label(date)}.txt")


# ──────────────────────────────────────────────────────────────────────────────
#  Budget management
# ──────────────────────────────────────────────────────────────────────────────
def load_or_create_budget(today: datetime.date) -> float:
    """
    • If a budget for *this* month exists → load it.
    • Otherwise (new month):
        - If today is the 1st and last month's budget exists, offer to reuse it.
        - Else ask the user for a new budget.
    """
    this_month_budget = budget_file_for(today)

    # 1. Already have a budget for this month
    if this_month_budget.exists():
        return float(this_month_budget.read_text().strip())

    # 2. Maybe reuse last month's budget?
    prev_month_date = (today.replace(day=1) - datetime.timedelta(days=1))
    prev_budget_path = budget_file_for(prev_month_date)
    if today.day == 1 and prev_budget_path.exists():
        prev_budget_value = float(prev_budget_path.read_text().strip())
        ans = input(
            f"🗓️  {today.strftime('%B %Y')} has begun.\n"
            f"Last month's budget was ₹{prev_budget_value:.2f}.\n"
            f"Continue with the same budget? (y/n): "
        ).strip().lower()
        if ans == "y":
            this_month_budget.write_text(str(prev_budget_value))
            return prev_budget_value

    # 3. Ask for a fresh budget
    while True:
        try:
            new_budget = float(
                input(f"💵 Enter budget for {today.strftime('%B %Y')} (₹): "))
            if new_budget < 0:
                print("Budget must be positive.")
                continue
            break
        except ValueError:
            print("Invalid number. Try again.")

    this_month_budget.write_text(str(new_budget))
    return new_budget


# ──────────────────────────────────────────────────────────────────────────────
#  Expense entry
# ──────────────────────────────────────────────────────────────────────────────
def get_user_expense() -> Expense:
    """Prompt user for a single expense record."""
    print("🎯  Enter a new expense")
    name = input("Name/Description: ").strip()

    while True:
        try:
            amt = float(input("Amount (₹): "))
            if amt < 0:
                print("Amount must be positive.")
                continue
            break
        except ValueError:
            print("Invalid number. Try again.")

    while True:
        print("Select a category:")
        for i, (cat, emj) in enumerate(EXPENSE_CATEGORIES, start=1):
            print(f"  {i:>2}. {emj} {cat}")
        try:
            idx = int(input(f"Choice [1‑{len(EXPENSE_CATEGORIES)}]: ")) - 1
            if 0 <= idx < len(EXPENSE_CATEGORIES):
                category = EXPENSE_CATEGORIES[idx][0]
                return Expense(name, category, amt)
            print("Invalid selection.")
        except ValueError:
            print("Please enter a number.")


def save_expense(exp: Expense, file_path: Path) -> None:
    """Append an expense row (date,name,amount,category) to CSV."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today()
    with file_path.open("a", encoding="utf-8") as f:
        f.write(f"{today},{exp.name},{exp.amount},{exp.category}\n")
    print("✅  Expense saved.\n")


# ──────────────────────────────────────────────────────────────────────────────
#  Reporting & visual summary
# ──────────────────────────────────────────────────────────────────────────────
def visual_summary(amount_by_cat: dict[str, float],
                    total_spent: float,
                    remaining_percent: float,budget:float) -> None:
    """Draw a pie chart with category shares and remaining budget."""
    labels = ["Remaining"]
    sizes = [remaining_percent]
    explode = [0.06]  # pop out remaining slice a bit

    for cat, amt in amount_by_cat.items():
        percent = (amt /budget) * 100 if budget else 0
        labels.append(cat)
        sizes.append(percent)
        explode.append(0)

    plt.figure(figsize=(7, 7))
    plt.pie(
        sizes,
        labels=labels,
        explode=explode,
        autopct="%1.1f%%",
        startangle=90
    )
    plt.title("Monthly Expense Distribution")
    plt.tight_layout()
    plt.show()


def summarize(expense_path: Path, budget: float) -> None:
    """Read expenses for the current month and print a summary."""
    if not expense_path.exists() or expense_path.stat().st_size == 0:
        print("📂  No expenses recorded yet.")
        return

    expenses: list[Expense] = []
    with expense_path.open(encoding="utf-8") as f:
        for line in f:
            try:
                _, name, amt, cat = line.strip().split(",")
                expenses.append(Expense(name, cat, float(amt)))
            except ValueError:
                print(f"Skipping malformed line: {line.strip()}")

    amount_by_cat: dict[str, float] = {}
    for exp in expenses:
        amount_by_cat[exp.category] = amount_by_cat.get(exp.category, 0) + exp.amount

    total_spent = sum(exp.amount for exp in expenses)
    remaining = budget - total_spent
    remaining_pct = (remaining / budget * 100) if budget else 0

    # CLI output
    print("\n🧾  Expense Summary — % of Total Spent")
    for cat, amt in amount_by_cat.items():
        pct = (amt / budget) * 100 if total_spent else 0
        pct = (amt / total_spent) * 100 if total_spent else 0   # base = spending
        emoji = next((e for c, e in EXPENSE_CATEGORIES if c == cat), "")
        print(f"  {emoji} {cat:<14} ₹{amt:>10.2f}  ({pct:>5.1f}%)")
    print(f"\nTotal spent:      ₹{total_spent:.2f}")
    print(f"Budget remaining: ₹{remaining:.2f}")

    # Daily budget left
    today = datetime.date.today()
    days_left = calendar.monthrange(today.year, today.month)[1] - today.day
    daily = remaining / days_left if days_left else 0
    print(green(f"Daily budget left: ₹{daily:.2f}\n"))

    # Optional pie chart
    if input("Show pie chart? (y/n): ").strip().lower() == "y":
        visual_summary(amount_by_cat, total_spent, remaining_pct,budget)


# ──────────────────────────────────────────────────────────────────────────────
#  Main program loop
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    today = datetime.date.today()
    print(f"🎯  Expense Tracker — {today.strftime('%B %Y')}")

    # Budget management
    budget = load_or_create_budget(today)

    # File for this month’s expenses
    exp_file = expense_file_for(today)

    # Optionally add a new expense
    if input("Add a new expense? (y/n): ").strip().lower() == "y":
        exp = get_user_expense()
        save_expense(exp, exp_file)

    # Show summary
    summarize(exp_file, budget)


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
