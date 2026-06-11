import typer
from rich.console import Console
from rich.text import Text
from rich import pretty
from rich.panel import Panel
from rich.table import Table
from chefai.db.models import init_db, insert_discounts, get_discounts

pretty.install()

app = typer.Typer(help="ChefAI – smart food planner")
db_app = typer.Typer(help="Database commands")
app.add_typer(db_app, name="db")


# --- hello command ---
@app.command()
def hello(text: str = typer.Option("Hello, World!", "--text", "-t", help="Text to print")):
    """Print a rainbow message."""
    rconsole = Console()
    colors = ["red", "orange1", "yellow", "green", "cyan", "blue", "magenta"]
    t = Text()
    for i, ch in enumerate(text):
        if ch.isspace():
            t.append(ch)
        else:
            t.append(ch, style=colors[i % len(colors)])
    rconsole.print(Panel(t, title="Message", title_align="left"))


# --- db sub-commands ---
@db_app.command()
def init():
    """Create the discounts table if it doesn't exist."""
    init_db()
    Console().print("[green]✓ Database initialized![/green]")


@db_app.command()
def add(
    store: str = typer.Option(..., prompt=True, help="Store name"),
    product: str = typer.Option(..., prompt=True, help="Product name"),
    category: str = typer.Option("", help="Category (e.g. Meat, Dairy)"),
    original_price: float = typer.Option(..., prompt=True, help="Original price"),
    discount_price: float = typer.Option(..., prompt=True, help="Discount price"),
):
    """Add a single discount to the database."""
    discount = {
        "store": store,
        "product": product,
        "category": category or None,
        "original_price": original_price,
        "discount_price": discount_price,
    }
    insert_discounts([discount])
    Console().print(f"[green]✓ Added {product} from {store}![/green]")


@db_app.command("list")
def db_list(
    store: str = typer.Option(None, "--store", "-s", help="Filter by store"),
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
):
    """List discounts, with optional filters."""
    rows = get_discounts(store=store, category=category)
    if not rows:
        Console().print("[yellow]No discounts found.[/yellow]")
        return

    table = Table(title="Discounts")
    table.add_column("ID", style="dim")
    table.add_column("Store", style="cyan")
    table.add_column("Product", style="white")
    table.add_column("Category", style="green")
    table.add_column("Orig €", justify="right")
    table.add_column("Disc €", justify="right", style="bold green")

    for row in rows:
        table.add_row(
            str(row["id"]),
            row["store"],
            row["product"],
            row["category"] or "",
            f'{row["original_price"]:.2f}',
            f'{row["discount_price"]:.2f}',
        )
    Console().print(table)


@app.command()
def seed():
    """Insert 5 sample discounts for testing."""
    init_db()
    sample = [
        {"store": "Lidl", "product": "Chicken Breast 500g", "category": "Meat", "original_price": 5.99, "discount_price": 3.99},
        {"store": "Lidl", "product": "Greek Yogurt 500g", "category": "Dairy", "original_price": 2.49, "discount_price": 1.49},
        {"store": "Kaufland", "product": "Pork Shoulder 1kg", "category": "Meat", "original_price": 6.99, "discount_price": 4.49},
        {"store": "Tesco", "product": "Salmon Fillet 200g", "category": "Fish", "original_price": 7.99, "discount_price": 5.49},
        {"store": "Kaufland", "product": "Orange Juice 1L", "category": "Drinks", "original_price": 1.99, "discount_price": 0.99},
    ]
    insert_discounts(sample)
    Console().print("[green]✓ Seeded 5 sample discounts![/green]")


if __name__ == "__main__":
    app()