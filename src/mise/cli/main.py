"""Mise CLI – command-line interface."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from rich import pretty

from mise.db.database import SessionLocal, init_db
from mise.db.crud import insert_discounts, get_discounts as crud_get_discounts

pretty.install()

app = typer.Typer(help="Mise – smart food planning system")
db_app = typer.Typer(help="Database commands")
scrape_app = typer.Typer(help="Scraper commands")
ai_app = typer.Typer(help="AI commands")
auth_app = typer.Typer(help="Authentication commands")
profile_app = typer.Typer(help="User profile & preferences")

app.add_typer(db_app, name="db")
app.add_typer(scrape_app, name="scrape")
app.add_typer(ai_app, name="ai")
app.add_typer(auth_app, name="auth")
app.add_typer(profile_app, name="profile")


# ─── Helper ─────────────────────────────────────────────────────────────

def _require_user():
    """Get the current user or exit with an error."""
    from mise.auth.auth import get_current_user
    user = get_current_user()
    if user is None:
        Console().print("[red]✗ No user logged in. Run 'mise auth login' first.[/red]")
        raise typer.Exit(code=1)
    return user


# ─── hello command ──────────────────────────────────────────────────────

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


# ─── db sub-commands ───────────────────────────────────────────────────

@db_app.command()
def init():
    """Create all database tables if they don't exist."""
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
    session = SessionLocal()
    try:
        discount = {
            "store": store,
            "product": product,
            "category": category or None,
            "original_price": original_price,
            "discount_price": discount_price,
        }
        insert_discounts(session, [discount])
        Console().print(f"[green]✓ Added {product} from {store}![/green]")
    finally:
        session.close()


@db_app.command("list")
def db_list(
    store: str = typer.Option(None, "--store", "-s", help="Filter by store"),
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
):
    """List discounts, with optional filters."""
    session = SessionLocal()
    try:
        rows = crud_get_discounts(session, store=store, category=category)
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
                str(row.id),
                row.store,
                row.product,
                row.category or "",
                f"{row.original_price:.2f}" if row.original_price else "",
                f"{row.discount_price:.2f}" if row.discount_price else "",
            )
        Console().print(table)
    finally:
        session.close()


@app.command()
def seed():
    """Insert 5 sample discounts for testing."""
    init_db()
    session = SessionLocal()
    try:
        sample = [
            {"store": "Lidl", "product": "Chicken Breast 500g", "category": "Meat", "original_price": 5.99, "discount_price": 3.99},
            {"store": "Lidl", "product": "Greek Yogurt 500g", "category": "Dairy", "original_price": 2.49, "discount_price": 1.49},
            {"store": "Kaufland", "product": "Pork Shoulder 1kg", "category": "Meat", "original_price": 6.99, "discount_price": 4.49},
            {"store": "Tesco", "product": "Salmon Fillet 200g", "category": "Fish", "original_price": 7.99, "discount_price": 5.49},
            {"store": "Kaufland", "product": "Orange Juice 1L", "category": "Drinks", "original_price": 1.99, "discount_price": 0.99},
        ]
        insert_discounts(session, sample)
        Console().print("[green]✓ Seeded 5 sample discounts![/green]")
    finally:
        session.close()


# ─── auth sub-commands ──────────────────────────────────────────────────

@auth_app.command()
def register(
    username: str = typer.Option(..., prompt=True, help="Choose a username"),
    email: str = typer.Option(..., prompt=True, help="Your email address"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Choose a password"),
):
    """Create a new account."""
    from mise.auth.auth import register as auth_register

    console = Console()
    try:
        user = auth_register(username=username, email=email, password=password)
        console.print(f"[green]✓ Account created for '{user.username}'![/green]")

        # Show verification code info
        from mise.email.verification import is_verification_required
        if is_verification_required():
            code = getattr(user, "_verification_code", None)
            if code:
                console.print(f"\n[yellow]📧 A verification code has been sent to {user.email}.[/yellow]")
                console.print(f"  Run [bold]mise auth verify {code}[/bold] to verify your email.")
                console.print(f"  (In development mode, the code is shown above in the email output.)")
            else:
                console.print(f"\n[yellow]📧 A verification code has been sent to {user.email}.[/yellow]")
                console.print(f"  Run [bold]mise auth verify <code>[/bold] to verify your email.")
        else:
            console.print(f"  Run [bold]mise auth login[/bold] to log in.")
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(code=1)


@auth_app.command()
def login(
    username: str = typer.Option(..., prompt=True, help="Username"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Password"),
):
    """Log in to your account."""
    from mise.auth.auth import login as auth_login

    console = Console()
    try:
        user = auth_login(username=username, password=password)
        console.print(f"[green]✓ Logged in as '{user.username}'![/green]")
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(code=1)


@auth_app.command()
def logout():
    """Log out of the current account."""
    from mise.auth.auth import logout as auth_logout

    console = Console()
    auth_logout()
    console.print("[green]✓ Logged out.[/green]")


@auth_app.command()
def whoami():
    """Show the currently logged-in user."""
    from mise.auth.auth import get_current_user

    console = Console()
    user = get_current_user()
    if user is None:
        console.print("[yellow]No user logged in.[/yellow]")
        console.print("  Run [bold]mise auth login[/bold] to log in.")
    else:
        verified = "✓ verified" if user.is_verified else "✗ not verified"
        console.print(f"[green]Logged in as:[/green] {user.username} (id={user.id}, email={user.email}) [{verified}]")


@auth_app.command()
def verify(
    code: str = typer.Argument(..., help="8-digit verification code sent to your email"),
):
    """Verify your email address with a verification code."""
    from mise.auth.auth import get_current_user
    from mise.email.verification import verify_code

    console = Console()
    user = get_current_user()
    if user is None:
        console.print("[red]✗ No user logged in. Run 'mise auth login' first.[/red]")
        raise typer.Exit(code=1)

    if user.is_verified:
        console.print("[green]✓ Your email is already verified![/green]")
        return

    success, message = verify_code(user.id, code)
    if success:
        console.print(f"[green]✓ {message}[/green]")
    else:
        console.print(f"[red]✗ {message}[/red]")
        raise typer.Exit(code=1)


@auth_app.command("resend-verification")
def resend_verification():
    """Resend the email verification code."""
    from mise.auth.auth import get_current_user
    from mise.email.verification import resend_verification as do_resend

    console = Console()
    user = get_current_user()
    if user is None:
        console.print("[red]✗ No user logged in. Run 'mise auth login' first.[/red]")
        raise typer.Exit(code=1)

    if user.is_verified:
        console.print("[green]✓ Your email is already verified![/green]")
        return

    success, message = do_resend(user.id)
    if success:
        console.print(f"[green]✓ {message}[/green]")
    else:
        console.print(f"[red]✗ {message}[/red]")
        raise typer.Exit(code=1)


# ─── profile sub-commands ───────────────────────────────────────────────

@profile_app.command()
def setup():
    """Interactive setup wizard for your profile and preferences."""
    from mise.user.profile import update_profile
    from mise.user.preferences import (
        add_allergy, add_dislike, add_liked_cuisine, add_preferred_store, add_meal_slot,
    )

    console = Console()
    user = _require_user()

    console.print(f"\n[bold]🧑 Profile Setup for {user.username}[/bold]\n")

    # Profile fields
    household_size = Prompt.ask("Household size", default="1")
    preferred_units = Prompt.ask("Preferred units", choices=["metric", "imperial"], default="metric")
    currency = Prompt.ask("Currency", default="EUR")
    cooking_skill = Prompt.ask("Cooking skill", choices=["beginner", "intermediate", "advanced"], default="intermediate")
    max_cook_time = Prompt.ask("Max cook time (minutes, leave empty for no limit)", default="")

    profile_kwargs = {
        "household_size": int(household_size),
        "preferred_units": preferred_units,
        "currency": currency,
        "cooking_skill": cooking_skill,
    }
    if max_cook_time:
        profile_kwargs["max_cook_time_min"] = int(max_cook_time)

    update_profile(user.id, **profile_kwargs)
    console.print("[green]✓ Profile saved![/green]\n")

    # Allergies
    console.print("[bold]⚠️  Allergies[/bold]")
    allergies_input = Prompt.ask("Allergies (comma-separated, leave empty for none)", default="")
    if allergies_input.strip():
        for allergy in allergies_input.split(","):
            allergy = allergy.strip()
            if allergy:
                add_allergy(user.id, allergy)
    console.print("")

    # Dislikes
    console.print("[bold]👎 Disliked ingredients[/bold]")
    dislikes_input = Prompt.ask("Disliked ingredients (comma-separated, leave empty for none)", default="")
    if dislikes_input.strip():
        for dislike in dislikes_input.split(","):
            dislike = dislike.strip()
            if dislike:
                add_dislike(user.id, dislike)
    console.print("")

    # Liked cuisines
    console.print("[bold]🍽️  Liked cuisines[/bold]")
    cuisines_input = Prompt.ask("Liked cuisines (comma-separated, e.g. Italian,Mexican)", default="")
    if cuisines_input.strip():
        for cuisine in cuisines_input.split(","):
            cuisine = cuisine.strip()
            if cuisine:
                add_liked_cuisine(user.id, cuisine)
    console.print("")

    # Preferred stores
    console.print("[bold]🏪 Preferred stores[/bold]")
    stores_input = Prompt.ask("Preferred stores (comma-separated, e.g. Lidl,Kaufland,Tesco)", default="")
    if stores_input.strip():
        for store in stores_input.split(","):
            store = store.strip()
            if store:
                add_preferred_store(user.id, store)
    console.print("")

    # Meal slots
    console.print("[bold]📅 Meal slots to plan[/bold]")
    meal_slots_input = Prompt.ask("Meal slots (comma-separated, e.g. breakfast,lunch,dinner)", default="breakfast,lunch,dinner")
    if meal_slots_input.strip():
        for slot in meal_slots_input.split(","):
            slot = slot.strip()
            if slot:
                add_meal_slot(user.id, slot)

    console.print("\n[bold green]✓ Setup complete![/bold green]")


@profile_app.command()
def show():
    """Show your current profile and preferences."""
    from mise.user.profile import get_profile
    from mise.user.preferences import list_preferences

    console = Console()
    user = _require_user()

    profile = get_profile(user.id)

    # Profile info
    table = Table(title=f"Profile: {user.username}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Username", user.username)
    table.add_row("Email", user.email)
    table.add_row("Household size", str(profile.household_size))
    table.add_row("Preferred units", profile.preferred_units or "metric")
    table.add_row("Currency", profile.currency or "EUR")
    table.add_row("Weekly budget", f"{profile.weekly_budget}" if profile.weekly_budget else "Not set")
    table.add_row("Cooking skill", profile.cooking_skill or "intermediate")
    table.add_row("Max cook time", f"{profile.max_cook_time_min} min" if profile.max_cook_time_min else "No limit")
    table.add_row("Language", profile.language or "en")
    console.print(table)

    # Preferences
    prefs = list_preferences(user.id)
    if prefs:
        pref_table = Table(title="Preferences")
        pref_table.add_column("Type", style="cyan")
        pref_table.add_column("Value", style="white")
        pref_table.add_column("Weight", justify="right")

        for pref in prefs:
            pref_table.add_row(pref.pref_type, pref.pref_value, f"{pref.weight:.1f}")
        console.print(pref_table)
    else:
        console.print("[yellow]No preferences set. Run 'mise profile setup' to configure.[/yellow]")


@profile_app.command("add-allergy")
def profile_add_allergy(
    allergy: str = typer.Argument(..., help="Allergy to add (e.g. peanuts)"),
):
    """Add a food allergy."""
    from mise.user.preferences import add_allergy as _add_allergy

    user = _require_user()
    _add_allergy(user.id, allergy)
    Console().print(f"[green]✓ Added allergy: {allergy}[/green]")


@profile_app.command("remove-allergy")
def profile_remove_allergy(
    allergy: str = typer.Argument(..., help="Allergy to remove"),
):
    """Remove a food allergy."""
    from mise.user.preferences import remove_allergy as _remove_allergy

    user = _require_user()
    removed = _remove_allergy(user.id, allergy)
    if removed:
        Console().print(f"[green]✓ Removed allergy: {allergy}[/green]")
    else:
        Console().print(f"[yellow]Allergy '{allergy}' not found.[/yellow]")


@profile_app.command("add-dislike")
def profile_add_dislike(
    ingredient: str = typer.Argument(..., help="Disliked ingredient to add"),
):
    """Add a disliked ingredient."""
    from mise.user.preferences import add_dislike as _add_dislike

    user = _require_user()
    _add_dislike(user.id, ingredient)
    Console().print(f"[green]✓ Added dislike: {ingredient}[/green]")


@profile_app.command("remove-dislike")
def profile_remove_dislike(
    ingredient: str = typer.Argument(..., help="Disliked ingredient to remove"),
):
    """Remove a disliked ingredient."""
    from mise.user.preferences import remove_dislike as _remove_dislike

    user = _require_user()
    removed = _remove_dislike(user.id, ingredient)
    if removed:
        Console().print(f"[green]✓ Removed dislike: {ingredient}[/green]")
    else:
        Console().print(f"[yellow]Dislike '{ingredient}' not found.[/yellow]")


@profile_app.command("like-cuisine")
def profile_like_cuisine(
    cuisine: str = typer.Argument(..., help="Cuisine to add (e.g. Italian)"),
):
    """Add a liked cuisine."""
    from mise.user.preferences import add_liked_cuisine as _add_liked_cuisine

    user = _require_user()
    _add_liked_cuisine(user.id, cuisine)
    Console().print(f"[green]✓ Added liked cuisine: {cuisine}[/green]")


@profile_app.command("unlike-cuisine")
def profile_unlike_cuisine(
    cuisine: str = typer.Argument(..., help="Cuisine to remove"),
):
    """Remove a liked cuisine."""
    from mise.user.preferences import remove_liked_cuisine as _remove_liked_cuisine

    user = _require_user()
    removed = _remove_liked_cuisine(user.id, cuisine)
    if removed:
        Console().print(f"[green]✓ Removed liked cuisine: {cuisine}[/green]")
    else:
        Console().print(f"[yellow]Liked cuisine '{cuisine}' not found.[/yellow]")


@profile_app.command("set-units")
def profile_set_units(
    units: str = typer.Argument(..., help="Preferred units: 'metric' or 'imperial'"),
):
    """Set your preferred units."""
    from mise.user.profile import update_profile

    if units not in ("metric", "imperial"):
        Console().print("[red]✗ Units must be 'metric' or 'imperial'[/red]")
        raise typer.Exit(code=1)

    user = _require_user()
    update_profile(user.id, preferred_units=units)
    Console().print(f"[green]✓ Preferred units set to: {units}[/green]")


@profile_app.command("set-budget")
def profile_set_budget(
    amount: float = typer.Argument(..., help="Weekly budget amount (e.g. 50)"),
):
    """Set your weekly food budget."""
    from mise.user.profile import update_profile

    user = _require_user()
    update_profile(user.id, weekly_budget=amount)
    Console().print(f"[green]✓ Weekly budget set to: €{amount:.2f}[/green]")


# ─── scrape sub-commands ────────────────────────────────────────────────

@scrape_app.command("run")
def scrape_run(
    store: Optional[str] = typer.Argument(None, help="Store name to scrape (e.g. lidl, kaufland, tesco)"),
    save: bool = typer.Option(False, "--save", "-s", help="Save results to the database"),
):
    """Run a scraper. Use store name or --all to run all scrapers."""
    from mise.scraper import scraper_registry

    console = Console()

    if store:
        try:
            items = asyncio.run(scraper_registry.run_one(store))
        except KeyError as e:
            console.print(f"[red]✗ {e}[/red]")
            raise typer.Exit(code=1)
    else:
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
        session = SessionLocal()
        try:
            dicts = [item.to_dict() for item in items]
            insert_discounts(session, dicts)
            console.print(f"[green]✓ Saved {len(items)} discounts to database![/green]")
        finally:
            session.close()


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
        table.add_row(name)
    console.print(table)


# ─── ai sub-commands ────────────────────────────────────────────────────

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

    session = SessionLocal()
    try:
        rows = crud_get_discounts(session)
    finally:
        session.close()

    if not rows:
        console.print("[yellow]No discounts in the database to summarize.[/yellow]")
        return

    # Build a text representation of discounts
    lines = []
    for row in rows:
        line = f"- {row.store}: {row.product} ({row.category or 'N/A'}) €{row.original_price:.2f} → €{row.discount_price:.2f}"
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