New feature: Ingredient categorization and composition.

Create a product categories enum: 
fruits
vegetables
grains
protein_foods
dairy_and_alternatives
fats_and_oils
processed_items
other


Create a new endpoint, "POST /update_categories":
- Collects all `product` entries that don't have a value for `category`. 
- Makes an LLM call to GPT 5 mini, prompting the LLM to assign each product a category from the available options.
- If the result is JSON parseable and has correct format, and no invalid product categories, then update the categories.