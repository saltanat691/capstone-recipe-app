# AI Agents Architecture

This document describes the AI agent system for the Recipe AI System, built using LangGraph for orchestration.

## Overview

The Recipe AI System uses a multi-agent architecture where specialized agents collaborate to generate personalized recipe recommendations, meal plans, and shopping lists.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input                                │
│  (ingredients, preferences, dietary restrictions, days)      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Workflow                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. Ingredient Agent                                  │  │
│  │     • Validates and enriches ingredient data         │  │
│  │     • Suggests substitutions                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  2. Recipe Agent                                      │  │
│  │     • Searches database with vector similarity       │  │
│  │     • Generates new recipes with LLM                 │  │
│  │     • Ranks and filters recipes                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  3. Nutrition Agent                                   │  │
│  │     • Calculates nutritional values                  │  │
│  │     • Checks balance and health                      │  │
│  │     • Provides recommendations                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  4. Menu Planner Agent                                │  │
│  │     • Creates multi-day meal plan                    │  │
│  │     • Optimizes variety and balance                  │  │
│  │     • Assigns recipes to days and meals              │  │
│  └──────────────────────────────────────────────────────┘  │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  5. Grocery List Agent                                │  │
│  │     • Aggregates ingredients                         │  │
│  │     • Organizes by category                          │  │
│  │     • Estimates costs                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  6. Safety Agent                                      │  │
│  │     • Validates dietary restrictions                 │  │
│  │     • Checks for allergens                           │  │
│  │     • Ensures food safety                            │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Complete Recommendations                         │
│  • Menu plan for N days                                      │
│  • Organized shopping list                                   │
│  • Nutritional information                                   │
│  • Safety validation results                                 │
└─────────────────────────────────────────────────────────────┘
```

## Shared State

All agents communicate through a shared state object defined in `state.py`:

```python
class RecipeAgentState(TypedDict):
    # User Input
    raw_user_input: str
    available_ingredients: list[str]
    dietary_restrictions: list[str]
    cuisine_preferences: list[str]
    servings: int
    days: int

    # Processing Results
    candidate_recipes: list[dict[str, Any]]
    selected_recipes: list[dict[str, Any]]
    nutrition_notes: str
    menu_plan: dict[str, Any]
    grocery_list: dict[str, Any]
    validation_warnings: list[str]
    metadata: dict[str, Any]
```

Each agent reads from and updates this shared state as it processes the request.

## Agent Details

### 1. Ingredient Agent

**File**: `ingredient_agent.py`

**Responsibilities**:
- Parse and normalize ingredient names
- Validate ingredients against database
- Categorize ingredients (protein, vegetable, grain, etc.)
- Suggest substitutions for missing ingredients
- Enrich ingredient data with metadata

**Key Functions**:
- `analyze_ingredients(state)` - Main entry point
- `suggest_substitutions(ingredient, restrictions)` - Find alternatives
- `validate_ingredient(ingredient)` - Check if ingredient is valid

**Future Implementation**:
- LLM-based ingredient understanding
- Database lookup for ingredient information
- Smart substitution recommendations

### 2. Recipe Agent

**File**: `recipe_agent.py`

**Responsibilities**:
- Search database for recipes matching ingredients
- Perform semantic search using pgvector
- Generate new recipes with LLM when needed
- Rank recipes by relevance and preference
- Filter by dietary restrictions

**Key Functions**:
- `find_recipes(state)` - Main search and ranking
- `generate_recipe(state)` - LLM-based recipe creation
- `rank_recipes(recipes, state)` - Score and sort recipes
- `filter_by_restrictions(recipes, restrictions)` - Apply filters

**Future Implementation**:
- Vector similarity search in PostgreSQL
- GPT-4 or Claude for recipe generation
- ML-based personalization
- Recipe rating system

### 3. Nutrition Agent

**File**: `nutrition_agent.py`

**Responsibilities**:
- Calculate nutritional values for recipes
- Aggregate nutrition across meal plan
- Check for balanced macronutrients
- Identify vitamin and mineral coverage
- Generate nutrition recommendations

**Key Functions**:
- `analyze_nutrition(state)` - Main nutritional analysis
- `calculate_recipe_nutrition(recipe)` - Per-recipe calculation
- `check_nutritional_balance(nutrition_data)` - Validate balance
- `suggest_improvements(state)` - LLM-based suggestions

**Future Implementation**:
- Nutrition database integration (USDA FoodData Central)
- Personalized daily requirements
- Macronutrient ratio optimization
- Micronutrient tracking

### 4. Menu Planner Agent

**File**: `menu_planner_agent.py`

**Responsibilities**:
- Organize recipes into multi-day meal plan
- Assign recipes to meal times (breakfast, lunch, dinner)
- Ensure variety across days
- Balance nutrition throughout the week
- Optimize ingredient usage
- Consider preparation complexity distribution

**Key Functions**:
- `create_menu_plan(state)` - Main planning logic
- `assign_recipes_to_days(recipes, days)` - Day assignment
- `assign_meal_times(recipe)` - Meal time classification
- `optimize_variety(menu_plan)` - Variety optimization
- `estimate_prep_schedule(menu_plan)` - Time management

**Future Implementation**:
- LLM-based meal time suggestions
- Genetic algorithm for optimization
- Batch cooking identification
- Leftover planning

### 5. Grocery List Agent

**File**: `grocery_list_agent.py`

**Responsibilities**:
- Extract ingredients from all recipes
- Aggregate quantities of same ingredients
- Normalize units and measurements
- Subtract ingredients user already has
- Organize by store category
- Estimate costs

**Key Functions**:
- `generate_grocery_list(state)` - Main generation
- `aggregate_ingredients(recipes)` - Combine quantities
- `categorize_items(ingredients)` - Store organization
- `subtract_available_ingredients(ingredients, available)` - Remove owned items
- `estimate_costs(ingredients)` - Price calculation
- `suggest_bulk_items(ingredients)` - Bulk buying opportunities

**Future Implementation**:
- Unit conversion library
- Price database integration
- Store-specific organization
- Seasonal pricing awareness

### 6. Safety Agent

**File**: `safety_agent.py`

**Responsibilities**:
- Validate dietary restriction compliance
- Check for allergens
- Ensure food safety (temperatures, handling)
- Identify dangerous ingredient combinations
- Validate nutritional appropriateness
- Final safety gate before user presentation

**Key Functions**:
- `validate_recommendations(state)` - Main validation
- `check_allergens(recipes, restrictions)` - Allergen detection
- `validate_dietary_restrictions(recipes, restrictions)` - Restriction compliance
- `check_food_safety(recipe)` - Safety concerns
- `validate_ingredient_combinations(ingredients)` - Dangerous combos
- `final_safety_check(state)` - Last gate

**Future Implementation**:
- Comprehensive allergen database
- FDA food safety guidelines
- LLM-based unusual combination detection
- Severity-based warning system

## Workflow Orchestration

**File**: `graph.py`

The `RecipeAgentGraph` class orchestrates all agents using LangGraph:

```python
graph = RecipeAgentGraph()
result = await graph.invoke({
    "available_ingredients": ["chicken", "rice", "tomatoes"],
    "dietary_restrictions": ["gluten-free"],
    "cuisine_preferences": ["italian"],
    "servings": 4,
    "days": 7
})
```

### Workflow Steps

1. **Ingredient Analysis** → Parse and validate ingredients
2. **Recipe Search** → Find matching recipes
3. **Nutrition Analysis** → Calculate nutritional values
4. **Menu Planning** → Create balanced meal plan
5. **Grocery List** → Generate shopping list
6. **Safety Validation** → Final safety check

### Error Handling

Each agent can:
- Retry on failure
- Skip and continue
- Fail workflow (for critical errors)

### Streaming Results

The graph supports streaming to provide incremental updates:

```python
async for update in graph.stream(user_input):
    print(f"Agent completed: {update['node']}")
```

## Implementation Status

### ✅ Completed
- Agent skeleton structure
- Shared state definition
- Logging infrastructure
- Module organization

### 🚧 In Progress
None yet - skeletons ready for implementation

### ⏳ Planned
- LLM integration (OpenAI/Anthropic)
- Database queries with vector search
- LangGraph workflow implementation
- Agent function implementations
- Error handling and retries
- Streaming support
- Progress tracking
- Cost estimation
- Performance optimization

## Usage Example

Once implemented, usage will be:

```python
from app.agents import get_agent_graph

# Get graph instance
graph = get_agent_graph()

# Prepare user input
user_request = {
    "available_ingredients": [
        "chicken breast",
        "rice",
        "broccoli",
        "onions",
        "garlic"
    ],
    "dietary_restrictions": ["gluten-free", "dairy-free"],
    "cuisine_preferences": ["asian", "mediterranean"],
    "servings": 4,
    "days": 7
}

# Execute workflow
result = await graph.invoke(user_request)

# Access results
print(result["menu_plan"])
print(result["grocery_list"])
print(result["nutrition_notes"])
print(result["validation_warnings"])
```

## Observability

All agents are instrumented with:
- **Structured logging** with `get_logger(__name__)`
- **LangSmith tracing** (automatic when configured)
- **OpenTelemetry spans** (automatic for async functions)

View traces in:
- LangSmith: https://smith.langchain.com
- Grafana/Tempo: http://localhost:3001

## Testing

Test individual agents:

```python
from app.agents import IngredientAgent

agent = IngredientAgent()
state = {
    "available_ingredients": ["chicken", "rice"],
    "dietary_restrictions": [],
    "cuisine_preferences": [],
    "servings": 4,
    "days": 7
}

result = await agent.analyze_ingredients(state)
```

## Development Guidelines

### Adding New Agents

1. Create new file in `app/agents/`
2. Define agent class with `__init__` and processing methods
3. Use `get_logger(__name__)` for logging
4. Update `state.py` if new state fields needed
5. Add agent to workflow in `graph.py`
6. Export in `__init__.py`

### Agent Best Practices

1. **Idempotent**: Agents should be safe to re-run
2. **Stateless**: No instance state between calls
3. **Logged**: Log all major operations
4. **Typed**: Use type hints for all parameters
5. **Documented**: Clear docstrings for all methods
6. **Error Handling**: Catch and log exceptions
7. **Validating**: Validate inputs before processing

## Next Steps

1. Implement LLM calls in agents
2. Add database queries for recipe search
3. Implement LangGraph workflow in `graph.py`
4. Add unit tests for each agent
5. Add integration tests for workflow
6. Optimize performance
7. Add caching where appropriate
8. Implement streaming results
9. Add cost tracking
10. Deploy to production

## Additional Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/docs/)
- [Multi-Agent Systems Guide](https://python.langchain.com/docs/use_cases/more/agents/)
- [State Management](https://langchain-ai.github.io/langgraph/concepts/#state)