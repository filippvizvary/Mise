# Mise — Architecture Proposal

> *"Mise en place" — everything in its place, ready before you cook.*

## 1. Vision

Mise is **not** a discount tracker. It is a **personal food planning system** that learns about you over time and helps you decide **what to eat**, **how to cook it**, and **where to buy the ingredients cheapest**.

The discount tracking that already exists is still valuable — it becomes one subsystem within a larger whole, helping you save money by knowing which store has the best discount on what you need.

### Core Loop

```
User Profile → Meal Suggestions → Recipe Selection → Shopping List → Price Comparison → Store Recommendation → Feedback → Learn → (repeat)
```

### Future Vision

Mise will eventually have a **web UI** and a **mobile app**. The CLI-first approach means all core logic must be UI-agnostic (in `mise/planner`, `mise/recipe`, etc.) so that a web API (FastAPI) and mobile frontend can be added later without rewriting business logic.

The system will be **multi-user** from the ground up — with login, authentication, and per-user data isolation. Each user has their own preferences, recipes, meal plans, shopping lists, inventory, and budget.

---

## 2. High-Level Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                      Presentation Layer                        │
│          CLI (Typer+Rich) | Web UI (future) | Mobile (future) │
├───────────────────────────────────────────────────────────────┤
│                      Auth & User Management                    │
│              (login, registration, per-user isolation)         │
├───────────────────────────────────────────────────────────────┤
│                      mise/planner                               │
│             (orchestrates everything below)                     │
├──────────┬──────────┬──────────┬───────────┬───────────────────┤
│  mise/   │  mise/   │  mise/   │  mise/    │  mise/            │
│  user    │  meal     │  recipe  │  shopping │  inventory        │
│          │          |          │           │                   │
│ Profile  │ Planning │ Finder   │ List Gen  │ Pantry Items      │
│ Auth     │ Schedule │ Import   │ Aggregator│ Due Date Tracking │
│ Prefs    │ Calendar │ Scraper  │ Comparer  │ Receipt OCR       │
│ History  │          │ Parser   │           │ Voice Input       │
│ Feedback │          │ Units    │           │                   │
├──────────┴──────────┴──────────┴───────────┴───────────────────┤
│  mise/budget    │    mise/input    │    mise/units              │
│  (tracker)     │    (voice/ocr)   │    (converter)              │
├────────────────────────────────────────────────────────────────┤
│                      mise/ai                                    │
│           (AI providers — already exists)                       │
├────────────────────────────────────────────────────────────────┤
│                      mise/scraper                                │
│         (Store discount scrapers — already exists)              │
│         NOTE: Only discounts, NOT regular prices                │
├────────────────────────────────────────────────────────────────┤
│                      mise/db                                    │
│      (SQLite now → PostgreSQL for multi-user later)             │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. New Modules & Their Responsibility

### 3.1 `mise/user` — User Profile, Auth & Preferences

**Multi-user system with authentication.**

Each user has their own:
- Profile & preferences
- Recipes & favorites
- Meal plans
- Shopping lists
- Inventory
- Budget history
- Feedback history

**Auth & User model:**

| Field | Type | Description |
|---|---|---|
| `id` | int | Auto-increment |
| `username` | str | Unique username |
| `email` | str | Unique email |
| `password_hash` | str | Bcrypt hashed password |
| `created_at` | datetime | Registration date |

**User Preferences model:**

| Field | Type | Description |
|---|---|---|
| `user_id` | int | FK to users |
| `dietary_restrictions` | list[str] | Vegetarian, vegan, gluten-free, etc. |
| `allergies` | list[str] | Peanuts, shellfish, dairy, etc. |
| `disliked_ingredients` | list[str] | Things the user doesn't eat |
| `liked_cuisines` | list[str] | Italian, Mexican, Japanese, etc. |
| `preferred_meals` | list[str] | Which meals to plan (breakfast, lunch, dinner, brunch, snack) |
| `household_size` | int | How many people to cook for |
| `preferred_units` | str | "metric" or "imperial" |
| `currency` | str | "EUR", "USD", etc. |
| `weekly_budget` | float | Optional weekly food budget |
| `preferred_stores` | list[str] | Ranked store preferences |
| `cooking_skill` | str | "beginner", "intermediate", "advanced" |
| `max_cook_time` | int | Max minutes they'll spend cooking |
| `language` | str | "en" (English only for now, expandable later) |

**Feedback model:**

| Field | Type | Description |
|---|---|---|
| `id` | int | Auto-increment |
| `user_id` | int | FK to users |
| `recipe_id` | str | Which recipe was rated |
| `meal_date` | date | When it was eaten |
| `rating` | int | 1–5 stars |
| `would_repeat` | bool | Would cook again? |
| `modifications` | str | What they changed |
| `notes` | str | Free-text feedback |

**How it learns:**
- After each planned meal, Mise asks: *How was it? Rate 1-5, any modifications?*
- Over time, AI builds a preference vector: which cuisines/ingredients/complexity levels score high
- Disliked ingredients from low ratings get added to `disliked_ingredients`
- High-rated recipes get weighted higher in future suggestions
- When a user gives positive feedback on a recipe found online, it's **automatically saved** to their recipe library with source attribution

### 3.2 `mise/meal` — Meal Planning

The **scheduler** that decides what goes on the calendar.

**Data model — MealPlan:**

| Field | Type | Description |
|---|---|---|
| `id` | int | Auto-increment |
| `user_id` | int | FK to users |
| `date` | date | Which day |
| `meal_type` | str | "breakfast", "lunch", "dinner", "brunch", "morning_snack", "afternoon_snack" |
| `recipe_id` | str | Linked recipe |
| `status` | str | "planned", "shopped", "cooked", "skipped" |
| `servings` | int | How many servings |
| `created_at` | datetime | When the plan was created |

**Planning logic (AI-assisted):**

1. Load user profile + preferences + feedback history
2. Consider what's already planned for the week (avoid repetition)
3. Consider what ingredients are already in inventory (reduce waste)
4. Consider what ingredients are already in the shopping list (efficiency)
5. Consider seasonal availability
6. Consider **current discounts** at preferred stores (only discounts — stores don't publish regular prices)
7. Generate 3-5 meal suggestions per slot
8. User picks one (or says "surprise me")
9. Repeat for each meal slot in the planning horizon

**CLI commands envisioned:**
```
mise plan week                    # Plan the next 7 days
mise plan day                     # Plan tomorrow
mise plan lunch --date 2026-06-15 # Plan a specific meal
mise plan suggest --meal dinner   # Just get suggestions, don't commit
mise plan show                    # Show current plan
mise plan clear                   # Clear the plan
```

### 3.3 `mise/recipe` — Recipe Finding, Import & Management

This is where Mise **finds recipes online**, **imports user-pasted recipes**, and manages the recipe library.

**Data model — Recipe:**

| Field | Type | Description |
|---|---|---|
| `id` | str | Slug or hash (e.g. "lasagne-bolognese") |
| `user_id` | int | FK to users (who saved this) |
| `title` | str | "Lasagne Bolognese" |
| `source_url` | str | Where it came from (if online) |
| `source_site` | str | "allrecipes.com", "varecha.sk", "manual", etc. |
| `source_type` | str | "online", "import_paste", "import_voice" |
| `rating` | float | Average rating from source site |
| `user_rating` | int | User's own rating (1-5) |
| `rating_count` | int | Number of ratings on source site |
| `prep_time_min` | int | Preparation time |
| `cook_time_min` | int | Cooking time |
| `total_time_min` | int | Total time |
| `servings` | int | Default servings |
| `difficulty` | str | "easy", "medium", "hard" |
| `cuisine` | str | "Italian", "Mexican", etc. |
| `tags` | list[str] | ["comfort food", "freezable", "weeknight"] |
| `ingredients` | list[Ingredient] | Structured ingredient list |
| `steps` | list[str] | Step-by-step instructions |
| `image_url` | str | Optional photo |
| `nutrition` | dict | Optional nutrition info |
| `is_saved` | bool | Whether user explicitly saved it |
| `auto_saved` | bool | Whether it was auto-saved after positive feedback |
| `created_at` | datetime | When it was added |

**Recipe import — two key flows:**

#### Flow 1: Paste a recipe → AI formats it

```
mise recipe import
→ Paste your recipe (Ctrl+D when done):
→ [user pastes messy recipe text]
→ 
→ AI parsed this recipe:
→   Title: Grandma's Apple Pie
→   Servings: 8
→   Prep time: 30 min
→   Cook time: 60 min
→   Ingredients:
→     - 6 large apples, peeled and sliced
→     - 3/4 cup sugar
→     - 2 tbsp flour
→     - 1 tsp cinnamon
→     - 2 pie crusts (9 inch)
→   Steps:
→     1. Preheat oven to 190°C (375°F)
→     2. Mix apples, sugar, flour, cinnamon
→     3. ...
→
→ Save this recipe? [Y/n/e=edit]: y
→ ✓ Recipe saved as "grandmas-apple-pie"
```

The AI prompt for this:
```
System: You are a recipe formatting assistant. The user will paste a recipe 
in any format — messy text, a screenshot description, or structured text. 
Parse it into a structured JSON format with: title, servings, prep_time_min, 
cook_time_min, ingredients (each with name, quantity, unit, category), 
steps (numbered list), difficulty, cuisine, and tags. If information is 
missing, make reasonable inferences. Always convert units to both metric 
and imperial.

User: Parse the following recipe into structured JSON:
{pasted_text}
```

#### Flow 2: Online recipe liked after eating → auto-save

When a user rates a meal 4 or 5 stars and the recipe came from an online source:
1. The recipe is **automatically saved** to their library with `auto_saved = True`
2. The `source_url` and `source_site` are preserved
3. A note is added: "Saved because you rated this 5/5 on 2026-06-12"
4. The recipe appears in their `mise recipe list` with a ⭐ marker

**Recipe finding strategy (online):**

1. **AI generates recipe candidates** — Given the user's preferences and meal slot, AI proposes meal names
2. **Recipe scraper searches the web** — For each candidate, scrape top recipe sites
3. **Parse and rank** — Pick the highest-rated recipe, parse it into structured data
4. **Unit conversion** — Convert all units to user's preferred system
5. **Store the recipe** — Save to DB for future reference

**CLI commands envisioned:**
```
mise recipe find "lasagne bolognese"    # Search for recipe online
mise recipe import                      # Interactive: paste a recipe, AI formats it
mise recipe import-url "https://..."    # Import from URL, AI parses it
mise recipe show <id>                   # Show full recipe details
mise recipe list                        # List saved recipes
mise recipe rate <id> 4                 # Rate a recipe (auto-saves if 4+)
```

### 3.4 `mise/shopping` — Shopping List & Discount Comparison

**⚠️ Important: Slovak stores (Lidl, Kaufland, Tesco, Billa) do NOT publish regular prices for all products. Only discount prices are available.** Therefore, price comparison is discount-only:

- For items **on discount**, show which store has the best discount
- For items **not on discount**, add them to the shopping list without a discount/store header — just as a regular item to buy
- No "compare regular prices" feature because that data simply doesn't exist

**Data model — ShoppingList:**

| Field | Type | Description |
|---|---|---|
| `id` | int | Auto-increment |
| `user_id` | int | FK to users |
| `created_at` | datetime | When the list was created |
| `date_range_start` | date | First day of planned meals |
| `date_range_end` | date | Last day of planned meals |
| `status` | str | "pending", "in_progress", "completed" |

**Data model — ShoppingListItem:**

| Field | Type | Description |
|---|---|---|
| `id` | int | Auto-increment |
| `list_id` | int | FK to ShoppingList |
| `ingredient_name` | str | Canonical ingredient name |
| `quantity_needed` | float | Total quantity needed |
| `unit_needed` | str | Unit for needed quantity |
| `in_pantry` | bool | Whether already in inventory |
| `checked` | bool | Has been purchased? |
| `has_discount` | bool | Whether a discount was found |
| `best_store` | str | Which store has the best discount (null if no discount) |
| `discount_price` | float | Discounted price (null if no discount) |
| `discount_percent` | int | Discount percentage (null if no discount) |
| `discount_valid_until` | date | When the discount expires |

**Discount comparison logic:**

1. For each ingredient in the meal plan, check if it's **already in inventory** (pantry)
2. If in inventory with enough quantity, mark as `in_pantry = True` ✅
3. If not in inventory, search the **discounts** table for matches using **fuzzy matching** (rapidfuzz)
4. If a discount is found, show: "🛒 Ground beef 500g → **Lidl** €3.99 (33% off, valid until June 18)"
5. If no discount is found, show: "🛒 Tomato sauce 400g — No discount available, add to regular shopping list"
6. Group shopping list by store for discounted items, then list non-discounted items separately

**Example shopping list output:**
```
🛒 Shopping List (June 12-18)
═══════════════════════════════

✅ IN PANTRY:
   • Pasta (2 × 500g bags)
   • Olive oil (1 × 750ml bottle)

🏷️ BEST DISCOUNTS BY STORE:

   📦 LIDL:
   • Ground beef 500g     €3.99  (was €5.99, -33%)
   • Greek yogurt 500g    €1.49  (was €2.49, -40%)
   Valid until: June 18

   📦 KAUFLAND:
   • Pork shoulder 1kg     €4.49  (was €6.99, -36%)

   📦 TESCO:
   • Salmon fillet 200g   €5.49  (was €7.99, -31%)

📋 REGULAR ITEMS (no discount found):
   • Tomato sauce 400g
   • Onion 1kg
   • Garlic 3 cloves

💡 Tip: Buy discounted items at Lidl + Kaufland (2 stops).
   Regular items can be bought at any store.
```

**CLI commands envisioned:**
```
mise shopping generate --days 7       # Generate shopping list for 7 days
mise shopping generate --date 2026-06-15  # For a specific day
mise shopping show                     # Show current shopping list
mise shopping compare                  # Compare discounts across stores
mise shopping check <item_id>          # Mark item as purchased (also adds to inventory)
mise shopping optimize                 # Re-optimize discount assignments
```

### 3.5 `mise/inventory` — Pantry & Due Date Tracking

**This is critical** — nothing should spoil. Inventory tracks what's in your kitchen and when it expires.

**Data model — InventoryItem:**

| Field | Type | Description |
|---|---|---|
| `id` | int | Auto-increment |
| `user_id` | int | FK to users |
| `name` | str | Item name ("Milk 1L") |
| `category` | str | "Dairy", "Meat", "Produce", "Pantry", "Frozen" |
| `quantity` | float | Amount |
| `unit` | str | "500g", "1L", "1 bag", etc. |
| `purchase_date` | date | When it was bought |
| `due_date` | date | When it expires (estimated or from receipt) |
| `store` | str | Where it was bought |
| `price` | float | How much it cost |
| `source` | str | How it was entered: "manual", "receipt_ocr", "voice", "shopping_checkoff" |
| `added_at` | datetime | When added to inventory |

**Due date tracking:**

- Items with upcoming due dates get highlighted:
  - 🟢 Fresh (> 5 days)
  - 🟡 Use soon (2-5 days)
  - 🔴 Expiring soon (< 2 days)
  - ⚠️ Expired
- Mise can suggest meals that use expiring ingredients first (waste reduction)
- Notifications: "Your milk expires tomorrow — consider using it in tonight's dinner"

**Input methods for adding items to inventory:**

#### Method 1: Manual entry
```
mise inventory add "milk" --quantity 1 --unit "1L" --due-date 2026-06-20 --category Dairy
```

#### Method 2: Receipt photo (OCR) 📸
```
mise inventory receipt
→ Take a photo of your receipt or provide a file path:
→ [user provides receipt image]
→ AI + OCR extracts items, prices, and dates
→ 
→ Found 8 items from Lidl receipt:
→   1. Milk 1L .................. €1.29  (est. due: June 20)
→   2. Ground beef 500g ........ €4.99  (est. due: June 16)
→   3. Bread 1 loaf ............ €1.49  (est. due: June 14)
→   4. Tomato sauce 400g ....... €0.99  (est. due: Dec 2026)
→   ...
→
→ Save all? [Y/n/e=edit]: y
→ ✓ 8 items added to inventory
```

#### Method 3: Voice dictation 🎙️
```
mise inventory voice
→ Listening... (press Enter when done)
→ 🎙️ "I bought milk 1 liter, ground beef 500 grams, bread, 
→    and tomatoes. The milk expires on June 20th, the beef 
→    should be used by Saturday."
→
→ AI transcribed and parsed:
→   1. Milk 1L .................. (due: June 20)
→   2. Ground beef 500g ........ (due: ~June 16, this Saturday)
→   3. Bread .................... (due: ~June 14, typical 3 days)
→   4. Tomatoes ................. (due: ~June 18, typical 5 days)
→
→ ✓ Correct? [Y/n/e=edit]: y
→ ✓ 4 items added to inventory
```

The voice input flow:
1. Audio is recorded (or received from a dedicated device with screen)
2. Audio is sent to a **transcription service** (Whisper API, or local Whisper model)
3. Transcribed text is sent to AI which parses it into structured items
4. AI estimates due dates based on food type knowledge (e.g., milk ~7 days, beef ~3-5 days, canned goods ~1 year)
5. Items are displayed on screen for confirmation
6. User presses a button to confirm/save

#### Method 4: Shopping list checkoff
When you check off an item from the shopping list as "purchased", it automatically gets added to inventory with an estimated due date.

**CLI commands envisioned:**
```
mise inventory add "milk" --qty 1 --unit "1L" --due 2026-06-20  # Manual add
mise inventory receipt                                            # OCR from receipt
mise inventory voice                                              # Voice input
mise inventory list                                               # List all items
mise inventory expiring                                           # Show items expiring soon
mise inventory use "milk"                                         # Mark item as used/consumed
mise inventory remove "milk"                                      # Remove from inventory
mise inventory suggest                                            # Suggest meals using expiring items
```

### 3.6 `mise/budget` — Budget Tracking

**Data model — BudgetEntry:**

| Field | Type | Description |
|---|---|---|
| `id` | int | Auto-increment |
| `user_id` | int | FK to users |
| `date` | date | Purchase date |
| `store` | str | Which store |
| `total_spent` | float | Total amount |
| `items` | list | What was bought |
| `planned` | bool | Was this from a mise shopping list? |

**CLI commands envisioned:**
```
mise budget show              # Current week's budget status
mise budget set 50            # Set weekly budget to €50
mise budget log --store Lidl --total 23.50  # Log a purchase
mise budget report            # Weekly/monthly spending report
```

### 3.7 `mise/units` — Unit Conversion

A dedicated module for converting between metric/imperial and between different units within the same system.

**Conversion pairs:**
- Weight: g ↔ oz ↔ lb
- Volume: ml ↔ fl oz ↔ cup ↔ tbsp ↔ tsp
- Temperature: °C ↔ °F
- Length: cm ↔ in (for pan sizes, etc.)
- Special: "1 stick butter" = 113g, "1 can" = 400g, "1 can tomato" = 400g

**CLI commands envisioned:**
```
mise units convert 500g oz    # 500g = 17.6 oz
mise units convert 2cups ml   # 2 cups = 473 ml
```

### 3.8 `mise/input` — Voice & OCR Input Processing

A dedicated module for processing non-text inputs:

- **Voice transcription** → Send audio to Whisper API → Get text → Send to AI for structured parsing → Return items/dates
- **Receipt OCR** → Send image to OCR (Tesseract or cloud OCR) → Get text → Send to AI for structured parsing → Return items/prices/dates

This module abstracts the input processing pipeline so both CLI and future web/mobile UIs can use it.

### 3.9 Existing modules — Changes

#### `mise/scraper` — Discounts ONLY

Scrapers fetch **discount prices only**. Slovak stores (Lidl, Kaufland, Tesco, Billa) do **not** publish regular prices for all products — they only publish weekly discount flyers. Therefore:

- Keep existing `scrape()` method for discounts
- **Do NOT add** a `scrape_products()` method for regular prices — this data is not available
- Price comparison is **discount-only**: compare which store has the best discount, and for items without discounts, just add them as regular (non-discounted) items to the shopping list

#### `mise/db` — Expanded schema

The current `discounts` table stays. Many new tables are added (see Section 4).

#### `mise/ai/prompts` — Many new prompts

New prompts for:
- Meal suggestion (given preferences, day, meal type)
- Recipe search query generation
- **Recipe import/formatting** (paste text → structured JSON)
- **Receipt OCR parsing** (OCR text → structured items/prices/dates)
- **Voice input parsing** (transcribed text → structured items/dates)
- Ingredient parsing from recipe text
- Unit conversion hints
- Preference learning from feedback
- Shopping list summarization
- Budget optimization advice
- **Due date estimation** (given food item name, estimate shelf life)

#### `mise/config` — New config entries

```python
# User defaults
DEFAULT_HOUSEHOLD_SIZE = 1
DEFAULT_UNITS = "metric"
DEFAULT_CURRENCY = "EUR"
DEFAULT_WEEKLY_BUDGET = None  # no budget limit by default
DEFAULT_LANGUAGE = "en"  # English only for now, expandable later

# Recipe sources
RECIPE_SOURCES = ["allrecipes.com", "bbcgoodfood.com", "varecha.sk"]

# Planning
DEFAULT_PLANNING_HORIZON_DAYS = 7
MEAL_SLOTS = ["breakfast", "lunch", "dinner"]

# Price comparison (discounts only — regular prices not available)
MAX_STORE_VISITS = 3  # don't recommend visiting more than 3 stores
PREFERRED_STORES_ORDER = []  # user preference, empty = no preference

# Voice input
WHISPER_MODEL = "base"  # Whisper model for transcription
WHISPER_LANGUAGE = "en"  # transcription language

# OCR
OCR_ENGINE = "tesseract"  # or "cloud" for cloud-based OCR
```

---

## 4. Database Schema (Proposed)

```sql
-- ─── Users & Auth ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
    household_size INTEGER DEFAULT 1,
    preferred_units TEXT DEFAULT 'metric',   -- 'metric' or 'imperial'
    currency TEXT DEFAULT 'EUR',
    weekly_budget REAL,
    cooking_skill TEXT DEFAULT 'intermediate',
    max_cook_time_min INTEGER,
    language TEXT DEFAULT 'en',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    pref_type TEXT NOT NULL,   -- 'allergy', 'dislike', 'liked_cuisine', 'preferred_store', 'meal_slot'
    pref_value TEXT NOT NULL,
    weight REAL DEFAULT 1.0    -- how strongly this preference counts
);

-- ─── Recipes ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recipes (
    id TEXT PRIMARY KEY,       -- slug like 'lasagne-bolognese'
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    source_url TEXT,            -- URL if from online, NULL if manual
    source_site TEXT,           -- "allrecipes.com", "varecha.sk", "manual", "import_paste", "import_voice"
    source_type TEXT DEFAULT 'manual',  -- 'online', 'import_paste', 'import_voice'
    rating REAL,                -- rating from source site
    user_rating INTEGER,        -- user's own 1-5 rating
    rating_count INTEGER,
    prep_time_min INTEGER,
    cook_time_min INTEGER,
    total_time_min INTEGER,
    servings INTEGER DEFAULT 4,
    difficulty TEXT,             -- 'easy', 'medium', 'hard'
    cuisine TEXT,
    image_url TEXT,
    instructions TEXT,           -- JSON array of steps
    is_saved INTEGER DEFAULT 1,  -- explicitly saved by user
    auto_saved INTEGER DEFAULT 0, -- auto-saved after positive feedback
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS recipe_tags (
    recipe_id TEXT NOT NULL REFERENCES recipes(id),
    tag TEXT NOT NULL,
    PRIMARY KEY (recipe_id, tag)
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id TEXT NOT NULL REFERENCES recipes(id),
    name TEXT NOT NULL,          -- canonical: "ground beef"
    quantity REAL,
    unit TEXT,                   -- original unit from recipe
    quantity_metric REAL,        -- converted to metric
    unit_metric TEXT,            -- "g" or "ml"
    quantity_imperial REAL,      -- converted to imperial
    unit_imperial TEXT,          -- "oz" or "fl oz"
    category TEXT,               -- "Meat", "Dairy", "Produce", "Pantry"
    is_optional INTEGER DEFAULT 0,
    notes TEXT
);

-- ─── Meal Planning ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS meal_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    date TEXT NOT NULL,          -- ISO date
    meal_type TEXT NOT NULL,     -- 'breakfast', 'lunch', 'dinner', 'brunch', 'snack_morning', 'snack_afternoon'
    recipe_id TEXT REFERENCES recipes(id),
    servings INTEGER,
    status TEXT DEFAULT 'planned',  -- 'planned', 'shopped', 'cooked', 'skipped'
    created_at TEXT DEFAULT (datetime('now'))
);

-- ─── Feedback ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    recipe_id TEXT REFERENCES recipes(id),
    meal_date TEXT,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    would_repeat INTEGER,       -- boolean as int
    modifications TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ─── Shopping Lists ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS shopping_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    date_range_start TEXT,
    date_range_end TEXT,
    status TEXT DEFAULT 'pending',  -- 'pending', 'in_progress', 'completed'
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS shopping_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id INTEGER NOT NULL REFERENCES shopping_lists(id),
    ingredient_name TEXT NOT NULL,
    quantity_needed REAL,
    unit_needed TEXT,
    in_pantry INTEGER DEFAULT 0,     -- whether item is already in inventory
    checked INTEGER DEFAULT 0,        -- whether purchased
    has_discount INTEGER DEFAULT 0,   -- whether a discount was found
    best_store TEXT,                  -- store with best discount (NULL if no discount)
    discount_price REAL,             -- discounted price (NULL if no discount)
    discount_percent INTEGER,        -- discount percentage (NULL if no discount)
    discount_valid_until TEXT        -- when discount expires (NULL if no discount)
);

-- ─── Inventory (Pantry + Due Dates) ───────────────────────
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,              -- "Milk 1L"
    category TEXT,                    -- "Dairy", "Meat", "Produce", "Pantry", "Frozen"
    quantity REAL,
    unit TEXT,                       -- "1L", "500g", "1 bag"
    purchase_date TEXT,              -- when bought
    due_date TEXT,                   -- when it expires (estimated or from receipt)
    store TEXT,                      -- where bought
    price REAL,                      -- how much it cost
    source TEXT DEFAULT 'manual',    -- 'manual', 'receipt_ocr', 'voice', 'shopping_checkoff'
    added_at TEXT DEFAULT (datetime('now'))
);

-- ─── Budget ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS budget_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    date TEXT NOT NULL,
    store TEXT,
    total_spent REAL,
    planned INTEGER DEFAULT 0,       -- was this from a mise shopping list?
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ─── Discounts (already exists, keep as-is) ────────────────
-- Only discount data is available from Slovak stores.
-- Regular prices are NOT scraped because stores don't publish them.
-- (existing table, no changes needed)
```

---

## 5. AI Prompt Strategy

The AI is the **brain** of Mise. Here's how prompts should be organized:

### 5.1 Meal Suggestion Prompt

```
System: You are a personal meal planning assistant. Given a user's preferences,
dietary restrictions, and past feedback, suggest meals for specific meal slots.
Consider: variety, balance, seasonal ingredients, prep time constraints, and
current store discounts. Return a JSON array of suggestions with: title, cuisine,
prep_time, brief description, and why it's a good fit.

User: Plan {meal_type} for {date}. 
User profile: {preferences}
Recent meals (avoid repeating): {recent_meals}
Items expiring soon in inventory: {expiring_items}
Current discounts at preferred stores: {discounts}
```

### 5.2 Recipe Import / Formatting Prompt

```
System: You are a recipe formatting assistant. The user will paste a recipe 
in any format — messy text, a copied recipe, or structured text. Parse it into 
a structured JSON format with: title, servings, prep_time_min, cook_time_min, 
ingredients (each with name, quantity, unit, category), steps (numbered list), 
difficulty, cuisine, and tags. Convert all units to both metric and imperial.
If information is missing, make reasonable inferences. Always include 
source_type as one of: "online", "import_paste", "import_voice".

User: Parse the following recipe into structured JSON:
{pasted_text}
```

### 5.3 Receipt OCR Parsing Prompt

```
System: You are a receipt parsing assistant. Given OCR text from a grocery store
receipt, extract individual items with their prices. Estimate expiration dates 
based on food type knowledge (e.g., milk ~7 days, bread ~3 days, canned goods 
~1 year). Return a JSON array with: name, price, category, estimated_due_date.

User: Parse the following receipt OCR text:
{ocr_text}
```

### 5.4 Voice Input Parsing Prompt

```
System: You are a grocery inventory assistant. The user has dictated what they 
bought, possibly including expiration dates. Parse the transcribed text into 
a list of grocery items with quantities, units, and due dates (if mentioned, 
otherwise estimate based on food type). Return JSON array with: name, quantity, 
unit, category, estimated_due_date, confidence.

User: Parse the following voice transcription:
{transcribed_text}
```

### 5.5 Recipe Parsing (from URL) Prompt

```
System: You are a recipe extraction assistant. Given recipe text or HTML from 
a cooking website, extract structured data: title, ingredients (with quantities 
and units), steps, prep/cook time, servings, difficulty, and cuisine. Return as JSON.
Always include the source_url and source_site.

User: Extract recipe from: {raw_text}
Source URL: {url}
```

### 5.6 Unit Conversion Prompt (fallback for edge cases)

```
System: You are a unit conversion assistant for cooking. Convert the given 
quantity and unit to the target system. Return ONLY the converted number and unit.

User: Convert {quantity} {unit} to {target_system}
```

### 5.7 Preference Learning Prompt

```
System: You are a food preference learning assistant. Given a user's meal 
feedback history, identify patterns: which cuisines they enjoy, which ingredients 
they dislike, preferred complexity levels, and any other insights. Return 
structured preferences as JSON.

User: Feedback history: {feedback_list}
Current preferences: {current_prefs}
```

### 5.8 Due Date Estimation Prompt

```
System: You are a food shelf life estimation assistant. Given a food item name
and category, estimate how many days it typically lasts from purchase. Consider
refrigeration, freezer storage, and pantry storage. Return JSON with: 
item, fridge_days, freezer_days, pantry_days, confidence.

User: Estimate shelf life for: {item_name} (category: {category})
```

### 5.9 Shopping Optimization Prompt (discounts only)

```
System: You are a grocery shopping optimizer. Given a list of ingredients needed
and current discounts at various stores, recommend which discounted items to 
buy where. For items without discounts, note them as "buy at any store".
Consider: total savings, number of store visits needed, and preferred stores.
Return JSON with recommended store assignments and estimated total cost.

Note: Only discount prices are available. Regular prices are not published by 
Slovak stores, so items without discounts should be listed separately.

User: Ingredients needed: {ingredients}
Current discounts: {discounts}
Preferred stores: {preferred}
```

---

## 6. CLI Command Structure (Proposed)

```
mise
├── auth                            # Authentication
│   ├── register                    # Create account
│   ├── login                       # Log in
│   ├── logout                      # Log out
│   └── whoami                      # Show current user
├── plan                            # Meal planning
│   ├── week                        # Plan next 7 days
│   ├── day                         # Plan tomorrow
│   ├── meal --type lunch --date    # Plan specific meal
│   ├── suggest                     # Get suggestions (don't save)
│   ├── show                        # Show current plan
│   └── clear                       # Clear plan
├── recipe                          # Recipe management
│   ├── find "lasagne bolognese"    # Search for recipe online
│   ├── import                      # Interactive: paste recipe, AI formats it
│   ├── import-url "https://..."    # Import from URL
│   ├── show <id>                   # Show recipe details
│   ├── list                        # List saved recipes
│   └── rate <id> 4                 # Rate a recipe (auto-saves if 4+)
├── shopping                        # Shopping lists
│   ├── generate --days 7           # Generate from meal plan
│   ├── show                        # Show current shopping list
│   ├── compare                     # Compare discounts across stores
│   ├── check <item>                # Mark item as purchased (adds to inventory)
│   └── optimize                    # Re-optimize discount assignments
├── inventory                       # Pantry & due date tracking
│   ├── add "milk" --qty 1 ...     # Manual add
│   ├── receipt                     # OCR from receipt photo
│   ├── voice                       # Voice input
│   ├── list                        # List all items
│   ├── expiring                    # Show items expiring soon
│   ├── use "milk"                  # Mark item as used/consumed
│   ├── remove "milk"               # Remove from inventory
│   └── suggest                     # Suggest meals using expiring items
├── budget                          # Budget tracking
│   ├── show                        # Current budget status
│   ├── set <amount>                # Set weekly budget
│   ├── log --store Lidl --total    # Log a purchase
│   └── report                      # Spending report
├── profile                         # User preferences
│   ├── setup                       # Interactive setup wizard
│   ├── show                        # Show current preferences
│   ├── add-allergy peanuts         # Add allergy
│   ├── add-dislike olives          # Add disliked ingredient
│   ├── like-cuisine Italian        # Add liked cuisine
│   └── set-units metric            # Set preferred units
├── units                           # Unit conversion
│   └── convert 500g oz             # Convert units
├── feedback                        # Meal feedback
│   ├── rate <recipe_id> 4          # Rate a meal
│   ├── note <recipe_id> "..."      # Add notes
│   └── prompt                      # Interactive feedback session
├── export                          # Data export/import
│   ├── recipes                     # Export recipes (JSON/CSV)
│   ├── plan                        # Export meal plan (iCal)
│   ├── shopping-list               # Export shopping list (text/markdown)
│   ├── inventory                   # Export inventory (JSON)
│   ├── preferences                 # Export preferences (JSON)
│   └── import <file>               # Import from JSON backup
├── scrape                          # (existing) Store discount scrapers
│   ├── run [store]                 # Run scrapers
│   └── list                        # List scrapers
├── db                              # (existing) Database commands
│   ├── init                        # Initialize DB
│   ├── add                         # Add discount
│   └── list                        # List discounts
├── ai                              # (existing) AI commands
│   ├── ask                         # Ask AI
│   ├── categorize                  # Categorize product
│   ├── summarize                   # Summarize discounts
│   ├── providers                   # List providers
│   └── health                      # Check provider health
└── hello                           # (existing) Easter egg
```

---

## 7. Recipe Import Flows

### 7.1 Paste Import (Interactive)

```
$ mise recipe import

Paste your recipe (Ctrl+D when done):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Grandma's Apple Pie

You'll need:
6 large apples (peeled and sliced)
3/4 cup sugar
2 tbsp flour
1 tsp cinnamon
2 pie crusts (9 inch)
2 tbsp butter

Preheat oven to 375F. Mix apples with sugar, flour, 
and cinnamon. Put in crust. Dot with butter. Top with 
second crust. Bake 45 minutes.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ AI parsed this recipe:

  Title:        Grandma's Apple Pie
  Servings:     8
  Prep time:    20 min
  Cook time:    45 min
  Difficulty:   easy
  Cuisine:      American
  
  Ingredients:
    • 6 large apples — peeled and sliced
    • ¾ cup sugar (177g / 6.25oz)
    • 2 tbsp flour (16g / 0.56oz)
    • 1 tsp cinnamon (3g / 0.1oz)
    • 2 pie crusts, 9 inch (23cm)
    • 2 tbsp butter (28g / 1oz)

  Steps:
    1. Preheat oven to 190°C (375°F)
    2. Mix apples with sugar, flour, and cinnamon
    3. Place mixture in pie crust
    4. Dot with butter
    5. Cover with second crust
    6. Bake for 45 minutes

Save this recipe? [Y/n/e=edit]: y
✓ Recipe saved as "grandmas-apple-pie"
```

### 7.2 Auto-Save After Positive Feedback

```
$ mise feedback rate lasagne-bolognese 5

✓ Rated 5/5! Since this recipe came from varecha.sk,
  it has been automatically saved to your recipe library.
  Source: https://www.varecha.sk/recept/lasagne-bolognese/
```

### 7.3 URL Import

```
$ mise recipe import-url "https://www.varecha.sk/recept/lasagne-bolognese/"

⏳ Fetching recipe from varecha.sk...
✨ Parsing recipe...

  Title:        Lasagne Bolognese
  Source:        varecha.sk
  Rating:        4.7/5 (312 ratings)
  Servings:     4
  Prep time:    30 min
  Cook time:    90 min
  Difficulty:   medium
  Cuisine:      Italian
  
  Ingredients:
    • 500g ground beef (1.1 lb)
    • 400g canned tomatoes
    • 250g lasagne sheets
    • 100g parmesan
    • ...

Save this recipe? [Y/n/e=edit]: y
✓ Recipe saved as "lasagne-bolognese"
```

---

## 8. Inventory & Due Date Tracking

### 8.1 Due Date Logic

Every item in inventory has a `due_date`. This can come from:
1. **Manual entry** — user specifies the date
2. **Receipt OCR** — some receipts include expiration dates
3. **Voice input** — user says "the milk expires on Friday"
4. **AI estimation** — based on food type (milk ~7 days, bread ~3 days, etc.)

### 8.2 Expiration Alerts

```
$ mise inventory expiring

⚠️ Expiring Soon:
  🔴 Milk 1L — expires TOMORROW (June 13)
  🟡 Ground beef 500g — expires in 2 days (June 14)
  🟡 Bread — expires in 3 days (June 15)

💡 Suggested meals using expiring items:
  1. Beef Stroganoff (uses ground beef, uses within 2 days)
  2. French Toast (uses bread, milk — uses both expiring items!)
```

### 8.3 Receipt OCR Flow

```
$ mise inventory receipt

📷 Provide receipt image path (or drag & drop): ./receipt_june12.jpg

⏳ Processing receipt with OCR...

✨ Found 6 items from Lidl receipt (June 12):

  #  Item                    Price    Est. Due Date
  1  Milk 1L                 €1.29    June 20 (8 days)
  2  Ground beef 500g        €4.99    June 16 (4 days)
  3  Bread 1 loaf            €1.49    June 15 (3 days)
  4  Tomato sauce 400g       €0.99    Dec 2026 (canned)
  5  Butter 250g             €1.99    July 2026 (2 months)
  6  Pasta 500g               €0.79    Dec 2026 (dry)

Save all items to inventory? [Y/n/e=edit]: y
✓ 6 items added to inventory
```

### 8.4 Voice Input Flow

```
$ mise inventory voice

🎙️ Listening... (press Enter when done speaking)
🎤 "I bought milk one liter, ground beef 500 grams, bread, 
     and tomatoes. The milk expires on June 20th."

⏳ Transcribing and parsing...

✨ I heard:

  #  Item                    Qty     Est. Due Date
  1  Milk 1L                 1       June 20 (as mentioned)
  2  Ground beef 500g        1       June 16 (~4 days, typical)
  3  Bread                   1       June 15 (~3 days, typical)
  4  Tomatoes                ?       June 18 (~5 days, typical)

  How many tomatoes? 3

  Updated:
  4  Tomatoes                3       June 18

Save all items to inventory? [Y/n/e=edit]: y
✓ 4 items added to inventory
```

**Dedicated device with screen**: In a future mobile/IoT version, the flow would be:
1. User presses a "record" button on the device
2. Speaks items into the device
3. Audio is transcribed → sent to AI → structured items displayed on screen
4. User confirms by pressing a "save" button
5. Items are added to inventory with due dates

---

## 9. Learning & Adaptation

### How Mise Learns

1. **Explicit preferences** — User sets them via `mise profile setup` or `mise profile add-*`
2. **Implicit from feedback** — After each meal, ask for 1-5 rating. Over time:
   - Low-rated recipes → lower cuisine/tag weights
   - High-rated recipes → boost those cuisines/tags
   - Common modifications → suggest modifications proactively
   - **Auto-save recipes rated 4+** — if from online source, save to library with attribution
3. **Implicit from behavior** — Track which suggested meals get skipped vs. accepted
4. **Seasonal awareness** — Suggest lighter meals in summer, heartier in winter
5. **Variety enforcement** — Never suggest the same cuisine 3 days in a row
6. **Inventory awareness** — Suggest meals that use expiring ingredients first

### Feedback Collection

After a planned meal's day passes:
```
$ mise feedback prompt

→ How was Lasagne Bolognese (June 12 lunch)?
  Rating (1-5): 4
  Any changes? Added more cheese on top
  Would you make it again? Yes

✓ Feedback saved! Recipe rated 4/5.
✓ Since this recipe came from varecha.sk, it has been
  automatically saved to your recipe library.
```

---

## 10. Multi-User & Auth

### Architecture

- Every table has a `user_id` foreign key
- All queries are scoped to the current user
- Login state is stored in a local token file (`~/.mise/auth`) for CLI
- For web/mobile: JWT-based authentication

### Auth Commands

```
mise auth register --username filip --email filip@example.com
mise auth login --username filip
mise auth logout
mise auth whoami
```

### Data Isolation

- User A cannot see User B's recipes, plans, inventory, etc.
- Discounts (from scrapers) are **shared** across all users — they're store data, not personal
- Recipes can be **private** (user-specific) or **shared** (public library in future)

---

## 11. Things I'd Add / Change

### 11.1 **Pantry Inventory & Due Date Tracking** 🏠expiration

Already covered in detail in Section 3.5. Key features:
- Track what's in your kitchen with due dates
- Nothing should spoil — get alerts and meal suggestions for expiring items
- Add items via manual entry, receipt photo (OCR), voice, or shopping checkoff
- Suggest meals that use expiring ingredients first

### 11.2 **Recipe Import (Paste & AI Format)** 📋

Already covered in Section 7.1. Key feature: paste any recipe text, AI automatically formats it into structured data with units converted.

### 11.3 **Auto-Save Liked Online Recipes** ⭐

Already covered in Section 7.2. When a user rates an online recipe 4+, it's auto-saved with source URL and attribution.

### 11.4 **Leftovers / Batch Cooking** 🍲

Plan for intentional leftovers:
- "Cook 4 servings of X, eat 2 today, refrigerate 2 for lunch tomorrow"
- "Make a big pot of soup, eat Mon/Wed/Fri"
- This reduces cooking effort and waste

### 11.5 **Nutritional Awareness** 🥗

Optional: track basic nutrition per meal (calories, protein, carbs, fat). Not a calorie counter, but enough to ensure balanced weeks.

### 11.6 **Meal Templates** 📋

Let users create templates like:
- "Weekday lunch: something quick, <30 min"
- "Sunday dinner: something fancy, can take 2 hours"
- "Post-workout: high protein"

### 11.7 **Shared Household** 👨‍👩‍👧‍👦

Even as a single DB, support `household_size > 1`:
- Scale recipes automatically (4-serving recipe for 2 people = halve ingredients)
- Consider different preferences per family member

### 11.8 **Import/Export** 📤📥

- **Export recipes** as JSON
- **Export meal plan** as iCal/Google Calendar
- **Export shopping list** as plain text, markdown, or PDF
- **Export inventory** as JSON
- **Export preferences** as JSON
- **Full backup/restore** — export everything, import everything
- **Import recipes** from URL (paste any cooking website URL)

### 11.9 **Notification Reminders** 🔔

Optional integration:
- "Tomorrow's lunch: Lasagne Bolognese — don't forget to thaw the ground beef!"
- "Your shopping list for the next 3 days has 7 items. Lidl has 3 of them on discount."
- "Your milk expires tomorrow — consider using it tonight!"

### 11.10 **Seasonal & Local Focus** 🌱

Since the user is in Slovakia (store URLs are `.sk`):
- Prioritize Slovak/European recipe sources (Varecha, Dobruchut)
- Suggest seasonal produce
- Consider local holidays (Christmas, Easter traditions)
- Support Slovak ingredient names alongside English
- Language support starts as **English only**, expandable to Slovak and others later

### 11.11 **Recipe Scaling** 📐

When `household_size != recipe.servings`:
- Automatically scale all ingredient quantities
- Handle edge cases (can't scale "1 egg" to "0.75 eggs" — round up)
- Show both original and scaled quantities

### 11.12 **Price History & Alerts** 📈

Even though regular prices aren't available:
- Track discount history per product per store
- Alert when a frequently-bought item goes on discount
- "Ground beef is on sale at Lidl for €3.99/kg this week — 33% off!"

### 11.13 **Web UI & Mobile App** 🖥️📱

Future phases:
- **Phase 7**: Web UI with FastAPI backend + React/Vue frontend
- **Phase 8**: Mobile app (React Native or Flutter)
- Core logic stays in `mise/` modules, UI is a thin layer
- The voice input flow is especially suited for mobile — record, transcribe, confirm, save

---

## 12. Price Comparison Strategy (Discounts Only)

**Important constraint**: Slovak stores (Lidl, Kaufland, Tesco, Billa) do **NOT** publish regular prices for their entire product catalog. They only publish **weekly discount flyers**.

Therefore, Mise's price comparison is **discount-only**:

### What Mise CAN do:
✅ Compare discounts across stores — "Ground beef is on sale at Lidl for €3.99 (33% off)"
✅ Tell you which store has the best discount for an item on your shopping list
✅ Group discounted items by store to minimize stops
✅ Track discount history over time — "This item goes on sale at Lidl every 6-8 weeks"

### What Mise CANNOT do:
❌ Compare regular prices between stores — this data doesn't exist publicly
❌ Tell you the regular price of an item not currently on sale
❌ Calculate exact total cost — only discounted items have prices

### Shopping list behavior:
- **Discounted items**: Show store, discount price, discount %, and expiry
- **Non-discounted items**: Show as "No discount available — buy at any store"
- Group discounted items by store for efficient shopping trips

---

## 13. Implementation Order (Suggested)

Building everything at once is overwhelming. Here's a phased approach:

### Phase 1 — Foundation (Current ✅)
- [x] Scraper infrastructure (Lidl, Kaufland, Tesco)
- [x] AI provider infrastructure (Ollama, OpenAI)
- [x] Basic DB (discounts table)
- [x] Basic CLI

### Phase 2 — User Auth & Profile & Recipe Core
- [ ] User authentication module (`mise/auth`) — register, login, logout
- [ ] Database schema expansion (users, profiles, preferences tables)
- [ ] User profile module (`mise/user`) — preferences, allergies, settings
- [ ] Recipe model & storage (`mise/recipe`)
- [ ] **Recipe import** — paste recipe, AI formats it, save to DB
- [ ] Recipe import from URL — AI parses web recipes
- [ ] Auto-save liked online recipes
- [ ] Unit conversion module (`mise/units`)
- [ ] CLI: `mise auth register/login`, `mise profile setup`, `mise recipe import`, `mise recipe show`

### Phase 3 — Meal Planning
- [ ] Meal plan model & storage (`mise/meal`)
- [ ] AI meal suggestion prompt (incorporating preferences + discounts)
- [ ] Meal plan calendar view
- [ ] CLI: `mise plan week`, `mise plan day`, `mise plan show`

### Phase 4 — Shopping & Inventory
- [ ] Shopping list model (`mise/shopping`) — discount-only price comparison
- [ ] Ingredient → discount fuzzy matching
- [ ] **Inventory module (`mise/inventory`)** — pantry items with due dates
- [ ] **Receipt OCR input** — parse receipt photos into inventory items
- [ ] **Voice input** — dictate items, transcribe, parse, confirm, save
- [ ] Expiration alerts and meal suggestions for expiring items
- [ ] Budget tracking (`mise/budget`)
- [ ] CLI: `mise shopping generate`, `mise inventory add/list/expiring`, `mise budget show`

### Phase 5 — Learning & Feedback
- [ ] Feedback collection (post-meal ratings)
- [ ] Preference learning (AI-driven updates to user profile)
- [ ] Suggestion quality improves over time
- [ ] CLI: `mise feedback rate`, `mise feedback prompt`

### Phase 6 — Polish & Extras
- [ ] Data export/import (JSON backup, iCal, PDF shopping lists)
- [ ] Meal templates
- [ ] Recipe scaling
- [ ] Leftovers/batch cooking support
- [ ] Discount history tracking & alerts
- [ ] Seasonal awareness
- [ ] Expand recipe scrapers (more sites)
- [ ] English language only (expand later)

### Phase 7 — Web UI (Future)
- [ ] FastAPI backend wrapping core `mise/` modules
- [ ] React/Vue frontend
- [ ] Authentication via web
- [ ] Mobile-responsive design

### Phase 8 — Mobile App (Future)
- [ ] React Native / Flutter app
- [ ] Camera integration for receipt photos
- [ ] Microphone for voice input
- [ ] Push notifications for expiring items, meal reminders

---

## 14. Key Technical Decisions

### 14.1 SQLite → PostgreSQL migration path
Start with SQLite for development speed. The schema is designed with `user_id` FKs so that when multi-user web support is needed, migrating to PostgreSQL is straightforward. The ORM/query layer should abstract DB operations so the migration is mostly config changes.

### 14.2 AI-first approach
Rather than building rigid rule engines, leverage the AI provider infrastructure that already exists. The AI should:
- Suggest meals (not a hard algorithm)
- Parse recipes (instead of fragile HTML parsers)
- Format pasted recipes (instead of manual entry)
- Parse receipt OCR (instead of brittle regex)
- Parse voice transcriptions (instead of structured voice commands)
- Estimate due dates (instead of hardcoded shelf life tables)
- Learn preferences (instead of manual tuning)
- Optimize shopping (considering tradeoffs)

### 14.3 Async scrapers, sync DB
Scrapers are async (Playwright/httpx). DB operations are sync (SQLite). This is fine for a CLI app. The `asyncio.run()` bridge in the CLI already works.

### 14.4 Pydantic models for all data
Every data model should be a Pydantic model first, then mapped to/from DB. This gives validation, serialization, and easy conversion.

### 14.5 Separation of concerns
- `mise/auth/` — user authentication, registration, login
- `mise/user/` — manages preferences and learning
- `mise/planner/` — orchestrates the meal planning workflow
- `mise/recipe/` — manages recipe data, import, export
- `mise/meal/` — manages meal plans and calendar
- `mise/shopping/` — manages shopping lists and discount comparison
- `mise/inventory/` — manages pantry items and due dates
- `mise/budget/` — manages budget
- `mise/input/` — voice transcription, receipt OCR
- `mise/units/` — converts units
- `mise/scraper/` — fetches discount data from the web
- `mise/ai/` — provides intelligence (suggestions, parsing, learning)
- `mise/db/` — persists everything
- `mise/cli/` — user interface

### 14.6 Discount-only price comparison
Since Slovak stores don't publish regular prices, Mise only compares discounts. Items without discounts are listed separately as "buy at any store." This is an intentional design constraint, not a limitation.

### 14.7 Language: English only for now
CLI, AI prompts, and internal data structures are in English. The architecture supports future localization via a `language` field in user preferences and i18n modules, but English-only is the starting point.

### 14.8 Config file for preferences
Use `~/.mise/config.yaml` for persistent settings (preferred stores, units, budget) rather than only environment variables. Env vars are good for secrets (API keys); config file is better for user preferences.

---

## 15. Open Questions

1. ~~**Should Mise have a web UI or stay CLI-only?**~~ — **Both.** CLI-first, then web UI (Phase 7), then mobile (Phase 8). Core logic must be UI-agnostic.

2. **Should recipe search be local or online?** — Start with online (scrape on demand), but cache results locally. Over time, build a local recipe library. User-pasted recipes are always local.

3. **How aggressive should the AI learning be?** — Should a single 1-star rating immediately deprioritize a cuisine, or should it take 3+ negative signals? Probably the latter — avoid overreaction.

4. ~~**Should we support multiple users?**~~ — **Yes.** Multi-user with auth from the start. Each user has isolated data.

5. **Recipe copyright?** — When scraping recipes, store the source URL prominently. Never claim recipes as our own. Consider just linking to recipes rather than fully copying them.

6. **Offline mode?** — Should Mise work without internet? Scraping requires internet, but viewing saved meal plans, recipes, and inventory should work offline.

7. ~~**Language?**~~ — **English only** to start. The architecture supports future localization. Slovak and other languages can be added later.

8. **Voice transcription provider?** — Should we use OpenAI Whisper API, a local Whisper model, or another service? Local Whisper is free but requires GPU; API is easier but costs money. Consider making it configurable.

9. **Receipt OCR provider?** — Tesseract (free, local) vs. cloud OCR services (Google Vision, AWS Textract). Start with Tesseract, add cloud options later.

---

*This document is a living blueprint. Each phase should be implemented step by step, with the architecture evolving as we learn what works.*