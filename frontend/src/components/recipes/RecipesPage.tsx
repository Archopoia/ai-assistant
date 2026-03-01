import React, { useMemo, useState } from 'react';
import { useRecipes } from '../../hooks/useMealPlanning';
import { nutritionAPI, recipesAPI } from '../../services/api';
import { MacroBreakdownChart } from '../charts/MacroBreakdownChart';
import type { Recipe } from '../../types';

export const RecipesPage: React.FC = () => {
  const [query, setQuery] = useState('high-protein vegetarian dinner');
  const [selected, setSelected] = useState<Recipe | null>(null);
  const [substitutions, setSubstitutions] = useState<string[]>([]);
  const [servings, setServings] = useState(2);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [recalculating, setRecalculating] = useState(false);
  const [logging, setLogging] = useState(false);
  const [selectedIngredient, setSelectedIngredient] = useState<string>('');
  const { recipes, loading } = useRecipes({ q: query });

  const selectedNutrition = useMemo(() => ({
    protein: Number(selected?.nutrition?.protein || 0),
    carbs: Number(selected?.nutrition?.carbs || 0),
    fats: Number(selected?.nutrition?.fats || 0),
  }), [selected]);

  const generateCustomRecipe = async () => {
    try {
      setGenerating(true);
      setError(null);
      setSuccess(null);
      const generated = await recipesAPI.generate({
        prompt: query,
        meal: 'dinner',
        servings,
      });
      setSelected(generated);
      setSuccess('Custom recipe generated.');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to generate recipe');
    } finally {
      setGenerating(false);
    }
  };

  const findSubstitutes = async (ingredientName: string) => {
    if (!selected) return;
    setSelectedIngredient(ingredientName);
    const data = await recipesAPI.substitute({
      recipe_id: selected.id,
      ingredient_name: ingredientName,
      available_ingredients: ['tofu', 'chickpeas', 'lentils', 'quinoa'],
    });
    setSubstitutions(data.substitutions || []);
  };

  const adjustPortions = async () => {
    if (!selected) return;
    try {
      setRecalculating(true);
      setError(null);
      setSuccess(null);
      const data = await recipesAPI.adjustPortion({ recipe_id: selected.id, servings });
      setSelected(data.recipe);
      setSuccess('Portion and nutrition updated.');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to recalculate portions');
    } finally {
      setRecalculating(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Recipes</h1>

      <div className="bg-white rounded-lg shadow-md p-6 space-y-3">
        <h2 className="text-xl font-semibold text-gray-900">Search & Filters</h2>
        <div className="flex flex-wrap gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name, ingredient, or cuisine"
            className="border rounded p-2 flex-1 min-w-[260px]"
          />
          <button className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-70" onClick={generateCustomRecipe} disabled={generating}>
            {generating ? 'Generating...' : 'Generate Custom Recipe'}
          </button>
        </div>
        <p className="text-sm text-gray-600">
          Filters are available via query parameters for dietary restrictions, allergies, calories/macros, and prep time.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900">Results</h2>
          {loading ? (
            <p className="text-gray-600">Loading recipes...</p>
          ) : (
            <div className="space-y-2 max-h-[540px] overflow-y-auto pr-1">
              {recipes.map((recipe) => (
                <button
                  key={recipe.id}
                  onClick={() => setSelected(recipe)}
                  className="w-full text-left border rounded p-3 hover:bg-gray-50"
                >
                  <div className="font-medium text-gray-900">{recipe.title}</div>
                  <div className="text-sm text-gray-600">
                    {recipe.cuisine} | {recipe.meal} | {recipe.time} min
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Calories: {Number(recipe.nutrition?.calories || 0).toFixed(0)} kcal
                    {recipe.dietary_tags?.length ? ` | Tags: ${recipe.dietary_tags.join(', ')}` : ''}
                  </div>
                </button>
              ))}
              {recipes.length === 0 && <p className="text-gray-600 text-sm">No recipes found.</p>}
            </div>
          )}
        </div>

        <div className="space-y-6">
          {selected ? (
            <>
              <div className="bg-white rounded-lg shadow-md p-6 space-y-3">
                <h2 className="text-xl font-semibold text-gray-900">{selected.title}</h2>
                <p className="text-sm text-gray-700">{selected.summary}</p>
                <p className="text-xs text-gray-500">
                  AI-generated from retrieved recipe context, then nutrition is computed with function calling.
                </p>
                {selected.img && (
                  <img
                    src={selected.img}
                    alt={selected.title}
                    className="w-full h-40 object-cover rounded border"
                    onError={(event) => {
                      event.currentTarget.style.display = 'none';
                    }}
                  />
                )}
                <div className="text-sm text-gray-600">
                  Servings: {selected.servings} | Time: {selected.time} min | Difficulty: {selected.difficulty_level}
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-sm text-gray-700">Adjust servings</label>
                  <input
                    type="number"
                    value={servings}
                    min={1}
                    onChange={(e) => setServings(Number(e.target.value))}
                    className="border rounded p-1 w-20"
                  />
                  <button className="bg-indigo-600 text-white px-3 py-1 rounded disabled:opacity-70" onClick={adjustPortions} disabled={recalculating}>
                    {recalculating ? 'Recalculating...' : 'Recalculate'}
                  </button>
                  <button
                    className="bg-purple-600 text-white px-3 py-1 rounded disabled:opacity-70"
                    disabled={logging}
                    onClick={async () => {
                      if (!selected) return;
                      try {
                        setLogging(true);
                        setError(null);
                        setSuccess(null);
                        await nutritionAPI.createLog({
                          meal_label: selected.title,
                          logged_at: new Date().toISOString(),
                          calories_kcal: Number(selected.nutrition?.calories || 0),
                          protein_g: Number(selected.nutrition?.protein || 0),
                          carbs_g: Number(selected.nutrition?.carbs || 0),
                          fats_g: Number(selected.nutrition?.fats || 0),
                          micronutrients: selected.nutrition?.micronutrients || {},
                        });
                        setSuccess(`Logged nutrition for "${selected.title}".`);
                      } catch (err: any) {
                        setError(err.response?.data?.detail || err.message || 'Failed to log nutrition');
                      } finally {
                        setLogging(false);
                      }
                    }}
                  >
                    {logging ? 'Logging...' : 'Log Nutrition'}
                  </button>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900 mb-2">Ingredients</h3>
                  <ul className="space-y-1 text-sm text-gray-700">
                    {selected.ingredients.map((ingredient) => (
                      <li key={ingredient.id} className="flex justify-between gap-2">
                        <span>
                          {ingredient.name} ({ingredient.quantity} {ingredient.unit || 'gram'})
                        </span>
                        <button
                          onClick={() => findSubstitutes(ingredient.name)}
                          className="text-xs text-blue-700 underline"
                        >
                          Substitute
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
                {substitutions.length > 0 && (
                  <div className="text-sm text-gray-700 border rounded p-3 bg-blue-50">
                    <strong>AI substitutions for {selectedIngredient}:</strong> {substitutions.join(', ')}
                  </div>
                )}
                <div>
                  <h3 className="font-medium text-gray-900 mb-2">Instructions</h3>
                  <ol className="list-decimal ml-5 text-sm text-gray-700 space-y-1">
                    {selected.preparation.map((step) => (
                      <li key={step.step}>
                        <strong>{step.step}:</strong> {step.description}
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
              <MacroBreakdownChart
                protein={selectedNutrition.protein}
                carbs={selectedNutrition.carbs}
                fats={selectedNutrition.fats}
              />
            </>
          ) : (
            <div className="bg-white rounded-lg shadow-md p-6 text-gray-600">Search or generate a custom recipe, then select one to see full details.</div>
          )}
        </div>
      </div>
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {success && <p className="text-green-700 text-sm">{success}</p>}
    </div>
  );
};
