"""Mise CLI – command-line interface for the discount tracker."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.text import Text
from rich import pretty
from rich.panel import Panel
from rich.table import Table

from mise.db.models import init_db, insert_discounts, get_discounts

pretty.install()

app = typer.Typer(help="Mise – smart food discount tracker")
db_app = typer.Typer(help="Database commands")
scrape_app = typer.Typer(help="Scraper commands")
ai_app = typer.Typer(help="AI commands")

app.add_typer(db_app, name="db")
app.add_typer(scrape_app, name="scrape")
app.add_typer(ai_app, name="ai")


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


# --- scrape sub-commands ---
@scrape_app.command("run")
def scrape_run(
    store: Optional[str] = typer.Argument(None, help="Store name to scrape (e.g. lidl, kaufland, tesco)"),
    save: bool = typer.Option(False, "--save", "-s", help="Save results to the database"),
):
    """Run a scraper. Use store name or --all to run all scrapers."""
    # Import here to trigger registration
    from mise.scraper import scraper_registry

    console = Console()

    if store:
        try:
            items = asyncio.run(scraper_registry.run_one(store))
        except KeyError as e:
            console.print(f"[red]✗ {e}[/red]")
            raise typer.Exit(code=1)
    else:
        # Run all scrapers
        items = asyncio.run(scraper_registry.run_all())

    if not items:
        console.print("[yellow]No discounts found.[/yellow]")
        return

    # Display results
    table = Table(title="Scraped Discounts")
    table.add_column("Store", style="cyan")
    table.add_column("Product", style="white")
    table.add_column("Category", style="green")
    table.add_column("Orig €", justify="right")
    table.add_column("Disc €", justify="right", style="bold green")
    table.add_column("%", justify="right", style="bold yellow")

    for item in items:
        table.add_row(
            item.store,
            item.product,
            item.category or "",
            f"{item.original_price:.2f}",
            f"{item.discount_price:.2f}",
            f"{item.discount_percent}%" if item.discount_percent else "",
        )
    console.print(table)

    if save:
        init_db()
        dicts = [item.to_dict() for item in items]
        insert_discounts(dicts)
        console.print(f"[green]✓ Saved {len(items)} discounts to database![/green]")


@scrape_app.command("list")
def scrape_list():
    """List all available scrapers."""
    from mise.scraper import scraper_registry

    console = Console()
    available = scraper_registry.list_available()
    if not available:
        console.print("[yellow]No scrapers registered.[/yellow]")
        return

    table = Table(title="Available Scrapers")
    table.add_column("Name", style="cyan")
    for name in available:
        scraper = scraper_registry.get(name)
        table.add_row(name)
    console.print(table)


# --- ai sub-commands ---
@ai_app.command("ask")
def ai_ask(
    question: str = typer.Argument(..., help="Question to ask the AI"),
    provider: str = typer.Option(None, "--provider", "-p", help="AI provider (e.g. ollama, openai)"),
    model: str = typer.Option(None, "--model", "-m", help="Model to use"),
):
    """Ask the AI a question about discounts or anything else."""
    from mise.ai import ai_registry

    console = Console()

    try:
        p = ai_registry.get(provider)
    except KeyError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(code=1)

    try:
        response = p.generate(question, model=model)
        console.print(Panel(response.content, title=f"AI ({response.provider}/{response.model})", title_align="left"))
    except Exception as e:
        console.print(f"[red]✗ AI error: {e}[/red]")
        raise typer.Exit(code=1)


@ai_app.command("categorize")
def ai_categorize(
    product: str = typer.Option(..., "--product", "-p", help="Product name to categorize"),
    store: str = typer.Option("", "--store", "-s", help="Store name for context"),
    provider: str = typer.Option(None, "--provider", "-P", help="AI provider"),
    model: str = typer.Option(None, "--model", "-m", help="Model to use"),
):
    """Use AI to categorize a grocery product."""
    from mise.ai import ai_registry
    from mise.ai.prompts import CATEGORIZE_SYSTEM, CATEGORIZE_PROMPT

    console = Console()

    try:
        p = ai_registry.get(provider)
    except KeyError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(code=1)

    prompt = CATEGORIZE_PROMPT.format(product=product, store=store)

    try:
        response = p.generate(prompt, system=CATEGORIZE_SYSTEM, model=model)
        console.print(Panel(
            f"Product: [bold]{product}[/bold]\nCategory: [green]{response.content}[/green]",
            title="Categorization",
            title_align="left",
        ))
    except Exception as e:
        console.print(f"[red]✗ AI error: {e}[/red]")
        raise typer.Exit(code=1)


@ai_app.command("summarize")
def ai_summarize(
    provider: str = typer.Option(None, "--provider", "-p", help="AI provider"),
    model: str = typer.Option(None, "--model", "-m", help="Model to use"),
):
    """Use AI to summarize current discounts in the database."""
    from mise.ai import ai_registry
    from mise.ai.prompts import SUMMARIZE_SYSTEM, SUMMARIZE_PROMPT

    console = Console()

    rows = get_discounts()
    if not rows:
        console.print("[yellow]No discounts in the database to summarize.[/yellow]")
        return

    # Build a text representation of discounts
    lines = []
    for row in rows:
        line = f"- {row['store']}: {row['product']} ({row['category'] or 'N/A'}) €{row['original_price']:.2f} → €{row['discount_price']:.2f}"
        lines.append(line)
    discounts_text = "\n".join(lines)

    prompt = SUMMARIZE_PROMPT.format(discounts=discounts_text)

    try:
        p = ai_registry.get(provider)
        response = p.generate(prompt, system=SUMMARIZE_SYSTEM, model=model)
        console.print(Panel(response.content, title="Discount Summary", title_align="left"))
    except Exception as e:
        console.print(f"[red]✗ AI error: {e}[/red]")
        raise typer.Exit(code=1)


@ai_app.command("providers")
def ai_providers():
    """List all available AI providers."""
    from mise.ai import ai_registry

    console = Console()
    available = ai_registry.list_available()
    default_name = ai_registry._default

    if not available:
        console.print("[yellow]No AI providers registered.[/yellow]")
        return

    table = Table(title="AI Providers")
    table.add_column("Name", style="cyan")
    table.add_column("Default", style="bold green")
    table.add_column("Default Model", style="white")

    for name in available:
        provider = ai_registry.get(name)
        is_default = "✓" if name == default_name else ""
        table.add_row(name, is_default, provider.default_model)

    console.print(table)


@ai_app.command("health")
def ai_health(
    provider: str = typer.Option(None, "--provider", "-p", help="AI provider to check"),
):
    """Check if an AI provider is reachable."""
    from mise.ai import ai_registry

    console = Console()

    try:
        p = ai_registry.get(provider)
    except KeyError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(code=1)

    if p.health_check():
        console.print(f"[green]✓ {p.name} is reachable![/green]")
    else:
        console.print(f"[red]✗ {p.name} is not reachable.[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()