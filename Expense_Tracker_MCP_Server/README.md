# Expense Tracker MCP Server

An interactive Model Context Protocol (MCP) server built with Python and [FastMCP](https://github.com/jlowin/fastmcp) for managing and analyzing personal/business expenses.

---

## 🌟 Overview & Progress

So far, we have built a complete, self-contained MCP server equipped with an SQLite backend, a flexible taxonomy system, dynamic tools, and MCP resources.

### What Has Been Built:
1. **FastMCP Server Integration**: Powered by `fastmcp` (v3.4.7+) and managed using `uv`.
2. **SQLite Database (`expenses.db`)**: Auto-initialized lightweight relational database storing expense records.
3. **Dynamic Category Taxonomy (`categories.json`)**: Configurable JSON schema defining 20 primary expense categories and subcategories.
4. **MCP Tools**: Functions exposed to AI clients to insert, list, and calculate expense summaries.
5. **MCP Resource (`expense://categories`)**: Exposes fresh category taxonomy to LLMs in real-time.

---

## 🏗️ Architecture & Database Schema

### Database Table: `expenses`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Unique identifier for each expense entry |
| `date` | `TEXT` | `NOT NULL` | Date of the expense (e.g., `YYYY-MM-DD`) |
| `amount` | `REAL` | `NOT NULL` | Numeric monetary amount spent |
| `category` | `TEXT` | `NOT NULL` | Main category (e.g., `food`, `transport`, `housing`) |
| `subcategory` | `TEXT` | `DEFAULT ''` | Specific subcategory (e.g., `groceries`, `fuel`) |
| `note` | `TEXT` | `DEFAULT ''` | Optional user description or memo |

---

## 🛠️ MCP Tools & Resources

### MCP Tools exposed in [`main.py`](file:///Users/shlokbam/Documents/Code/MCP%20%28Model%20Context%20Protocol%29/Expense_Tracker_MCP_Server/main.py)

1. **`add_expense`**
   - **Description**: Add a new expense entry to SQLite database.
   - **Parameters**: `date`, `amount`, `category`, `subcategory=""`, `note=""`
   - **Returns**: `{"status": "ok", "id": <lastrowid>}`

2. **`list_expenses`**
   - **Description**: Fetch all expense entries within an inclusive date range.
   - **Parameters**: `start_date`, `end_date`
   - **Returns**: Array of expense objects containing `id`, `date`, `amount`, `category`, `subcategory`, and `note`.

3. **`summarize`**
   - **Description**: Summarizes total expenses grouped by category within an inclusive date range, with an optional category filter.
   - **Parameters**: `start_date`, `end_date`, `category=None`
   - **Returns**: Array of objects with `category` and `total_amount`.

### MCP Resource

- **URI**: `expense://categories` (`application/json`)
- **Function**: `categories()`
- **Description**: Dynamically reads [`categories.json`](file:///Users/shlokbam/Documents/Code/MCP%20%28Model%20Context%20Protocol%29/Expense_Tracker_MCP_Server/categories.json) on every request, providing up-to-date category and subcategory definitions without requiring a server restart.

---

## 🏷️ Category Taxonomy ([`categories.json`](file:///Users/shlokbam/Documents/Code/MCP%20%28Model%20Context%20Protocol%29/Expense_Tracker_MCP_Server/categories.json))

The server currently supports 20 structured main categories with granular subcategories:

- **Food**: `groceries`, `fruits_vegetables`, `dairy_bakery`, `dining_out`, `coffee_tea`, `snacks`, `delivery_fees`, `other`
- **Transport**: `fuel`, `public_transport`, `cab_ride_hailing`, `parking`, `tolls`, `vehicle_service`, `other`
- **Housing**: `rent`, `maintenance_hoa`, `property_tax`, `repairs_service`, `cleaning`, `furnishing`, `other`
- **Utilities**: `electricity`, `water`, `gas`, `internet_broadband`, `mobile_phone`, `tv_dth`, `other`
- **Health**: `medicines`, `doctor_consultation`, `diagnostics_labs`, `insurance_health`, `fitness_gym`, `other`
- **Education**: `books`, `courses`, `online_subscriptions`, `exam_fees`, `workshops`, `other`
- **Family & Kids**: `school_fees`, `daycare`, `toys_games`, `clothes`, `events_birthdays`, `other`
- **Entertainment**: `movies_events`, `streaming_subscriptions`, `games_apps`, `outing`, `other`
- **Shopping**: `clothing`, `footwear`, `accessories`, `electronics_gadgets`, `appliances`, `home_decor`, `other`
- **Subscriptions**: `saas_tools`, `cloud_ai`, `newsletters`, `music_video`, `storage_backup`, `other`
- **Personal Care**: `salon_spa`, `grooming`, `cosmetics`, `hygiene`, `other`
- **Gifts & Donations**: `gifts_personal`, `charity_donation`, `festivals`, `other`
- **Finance & Fees**: `bank_charges`, `late_fees`, `interest`, `brokerage`, `other`
- **Business**: `software_tools`, `hosting_domains`, `marketing_ads`, `contractor_payments`, `travel_business`, `office_supplies`, `other`
- **Travel**: `flights`, `hotels`, `train_bus`, `visa_passport`, `local_transport`, `food_travel`, `other`
- **Home**: `household_supplies`, `cleaning_supplies`, `kitchenware`, `small_repairs`, `pest_control`, `other`
- **Pet**: `food`, `vet`, `grooming`, `supplies`, `other`
- **Taxes**: `income_tax`, `gst`, `professional_tax`, `filing_fees`, `other`
- **Investments**: `mutual_funds`, `stocks`, `fd_rd`, `gold`, `crypto`, `brokerage_fees`, `other`
- **Misc**: `uncategorized`, `rounding`, `other`

---

## 🚀 How to Run & Develop

### 1. Prerequisites & Environment Setup
Ensure you have `uv` installed. Activate the environment if needed:

```zsh
source .venv/bin/activate
```

### 2. Run FastMCP Dev Inspector
Launch the interactive FastMCP Dev Inspector UI:

```zsh
uv run fastmcp dev inspector main.py
```

### 3. Run Production Server
To run the server over stdio for integration with MCP Clients (e.g. Claude Desktop):

```zsh
uv run python main.py
```
