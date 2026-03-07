import React, { useEffect, useMemo, useState } from 'react';
import { useRecipes } from '../../hooks/useMealPlanning';
import { nutritionAPI, recipesAPI } from '../../services/api';
import { MacroBreakdownChart } from '../charts/MacroBreakdownChart';
import type { Recipe } from '../../types';
import { ALLERGIES_INTOLERANCES, DIETARY_PREFERENCES } from '../../utils/constants';

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
  const [filterCuisine, setFilterCuisine] = useState('');
  const [filterDietary, setFilterDietary] = useState('');
  const [filterAllergy, setFilterAllergy] = useState('');
  const [filterIngredient, setFilterIngredient] = useState('');
  const [maxCalories, setMaxCalories] = useState<number | ''>('');
  const [minProtein, setMinProtein] = useState<number | ''>('');
  const [maxProtein, setMaxProtein] = useState<number | ''>('');
  const [minCarbs, setMinCarbs] = useState<number | ''>('');
  const [maxCarbs, setMaxCarbs] = useState<number | ''>('');
  const [minFats, setMinFats] = useState<number | ''>('');
  const [maxFats, setMaxFats] = useState<number | ''>('');
  const [maxPrepTime, setMaxPrepTime] = useState<number | ''>('');
  const [minVitaminD, setMinVitaminD] = useState<number | ''>('');
  const [minVitaminB12, setMinVitaminB12] = useState<number | ''>('');
  const [minIron, setMinIron] = useState<number | ''>('');
  const [availableIngredientsInput, setAvailableIngredientsInput] = useState('tofu, chickpeas, lentils, quinoa');
  const [verifiedRecipes, setVerifiedRecipes] = useState<Recipe[]>([]);
  const [moderationQueue, setModerationQueue] = useState<Recipe[]>([]);
  const [loadingCommunity, setLoadingCommunity] = useState(false);

  const recipeQuery = useMemo(
    () => ({
      q: query || undefined,
      cuisine: filterCuisine || undefined,
      dietary_restrictions: filterDietary ? [filterDietary] : undefined,
      allergies: filterAllergy ? [filterAllergy] : undefined,
      ingredients: filterIngredient ? [filterIngredient] : undefined,
      max_calories: maxCalories === '' ? undefined : Number(maxCalories),
      min_protein: minProtein === '' ? undefined : Number(minProtein),
      max_protein: maxProtein === '' ? undefined : Number(maxProtein),
      min_carbs: minCarbs === '' ? undefined : Number(minCarbs),
      max_carbs: maxCarbs === '' ? undefined : Number(maxCarbs),
      min_fats: minFats === '' ? undefined : Number(minFats),
      max_fats: maxFats === '' ? undefined : Number(maxFats),
      max_prep_time: maxPrepTime === '' ? undefined : Number(maxPrepTime),
      min_vitamin_d_mcg: minVitaminD === '' ? undefined : Number(minVitaminD),
      min_vitamin_b12_mcg: minVitaminB12 === '' ? undefined : Number(minVitaminB12),
      min_iron_mg: minIron === '' ? undefined : Number(minIron),
    }),
    [
      query,
      filterCuisine,
      filterDietary,
      filterAllergy,
      filterIngredient,
      maxCalories,
      minProtein,
      maxProtein,
      minCarbs,
      maxCarbs,
      minFats,
      maxFats,
      maxPrepTime,
      minVitaminD,
      minVitaminB12,
      minIron,
    ]
  );

  const { recipes, loading } = useRecipes(recipeQuery);

  const loadCommunityFeatures = async () => {
    try {
      setLoadingCommunity(true);
      const [verified, queue] = await Promise.all([
        recipesAPI.getVerifiedRecommendations(6).catch(() => []),
        recipesAPI.getModerationQueue(10).catch(() => []),
      ]);
      setVerifiedRecipes(verified || []);
      setModerationQueue(queue || []);
    } finally {
      setLoadingCommunity(false);
    }
  };

  useEffect(() => {
    loadCommunityFeatures();
  }, []);

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
      await loadCommunityFeatures();
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
      available_ingredients: availableIngredientsInput
        .split(',')
        .map((item) => item.trim().toLowerCase())
        .filter(Boolean),
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

  const moderateRecipe = async (recipeId: string, action: 'approve' | 'reject' | 'flag') => {
    try {
      setError(null);
      setSuccess(null);
      await recipesAPI.moderate(recipeId, action);
      const actionLabel = action === 'approve' ? 'approved' : action === 'reject' ? 'rejected' : 'flagged';
      setSuccess(`Recipe ${actionLabel} successfully.`);
      await loadCommunityFeatures();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed moderation action');
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <input value={filterCuisine} onChange={(e) => setFilterCuisine(e.target.value)} placeholder="Cuisine filter" className="border rounded p-2" />
          <input value={filterIngredient} onChange={(e) => setFilterIngredient(e.target.value)} placeholder="Ingredient filter" className="border rounded p-2" />
          <input type="number" value={maxCalories} onChange={(e) => setMaxCalories(e.target.value === '' ? '' : Number(e.target.value))} placeholder="Max calories" className="border rounded p-2" />
          <select value={filterDietary} onChange={(e) => setFilterDietary(e.target.value)} className="border rounded p-2">
            <option value="">Dietary restriction</option>
            {DIETARY_PREFERENCES.map((pref) => (
              <option key={pref} value={pref}>{pref.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <select value={filterAllergy} onChange={(e) => setFilterAllergy(e.target.value)} className="border rounded p-2">
            <option value="">Allergy/intolerance</option>
            {ALLERGIES_INTOLERANCES.map((item) => (
              <option key={item} value={item}>{item.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <input type="number" value={maxPrepTime} onChange={(e) => setMaxPrepTime(e.target.value === '' ? '' : Number(e.target.value))} placeholder="Max prep time (min)" className="border rounded p-2" />
          <input type="number" value={minProtein} onChange={(e) => setMinProtein(e.target.value === '' ? '' : Number(e.target.value))} placeholder="Min protein (g)" className="border rounded p-2" />
          <input type="number" value={maxProtein} onChange={(e) => setMaxProtein(e.target.value === '' ? '' : Number(e.target.value))} placeholder="Max protein (g)" className="border rounded p-2" />
          <input type="number" value={minCarbs} onChange={(e) => setMinCarbs(e.target.value === '' ? '' : Number(e.target.value))} placeholder="Min carbs (g)" className="border rounded p-2" />
          <input type="number" value={maxCarbs} onChange={(e) => setMaxCarbs(e.target.value === '' ? '' : Number(e.target.value))} placeholder="Max carbs (g)" className="border rounded p-2" />
          <input type="number" value={minFats} onChange={(e) => setMinFats(e.target.value === '' ? '' : Number(e.target.value))} placeholder="Min fats (g)" className="border rounded p-2" />
          <input type="number" value={maxFats} onChange={(e) => setMaxFats(e.target.value === '' ? '' : Number(e.target.value))} placeholder="Max fats (g)" className="border rounded p-2" />
          <input type="number" value={minVitaminD} onChange={(e) => setMinVitaminD(e.target.value === '' ? '' : Number(e.target.value))} placeholder="Min Vitamin D (mcg)" className="border rounded p-2" />
          <input type="number" value={minVitaminB12} onChange={(e) => setMinVitaminB12(e.target.value === '' ? '' : Number(e.target.value))} placeholder="Min Vitamin B12 (mcg)" className="border rounded p-2" />
          <input type="number" value={minIron} onChange={(e) => setMinIron(e.target.value === '' ? '' : Number(e.target.value))} placeholder="Min Iron (mg)" className="border rounded p-2" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">Verified Recommendations</h2>
            <button
              className="text-sm text-blue-700 underline disabled:opacity-60"
              onClick={loadCommunityFeatures}
              disabled={loadingCommunity}
            >
              {loadingCommunity ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
          <p className="text-xs text-gray-500">Highly rated, moderation-approved recipes from community feedback.</p>
          <div className="space-y-2">
            {verifiedRecipes.map((recipe) => (
              <button
                key={`verified-${recipe.id}`}
                onClick={() => setSelected(recipe)}
                className="w-full text-left border rounded p-3 hover:bg-gray-50"
              >
                <div className="font-medium text-gray-900">{recipe.title}</div>
                <div className="text-xs text-gray-600">
                  Rating: {Number(recipe.rating_avg || 0).toFixed(2)} ({recipe.rating_count || 0} votes) | status: {recipe.moderation_status || 'approved'}
                </div>
              </button>
            ))}
            {!verifiedRecipes.length && <p className="text-sm text-gray-600">No verified recommendations yet.</p>}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 space-y-3">
          <h2 className="text-xl font-semibold text-gray-900">Moderation Queue</h2>
          <p className="text-xs text-gray-500">Pending/flagged generated recipes for quality control.</p>
          <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
            {moderationQueue.map((recipe) => (
              <div key={`moderation-${recipe.id}`} className="border rounded p-3">
                <div className="font-medium text-gray-900">{recipe.title}</div>
                <div className="text-xs text-gray-600 mb-2">Current status: {recipe.moderation_status || 'pending'}</div>
                <div className="flex gap-2">
                  <button className="text-xs px-2 py-1 rounded bg-green-50 text-green-700" onClick={() => moderateRecipe(recipe.id, 'approve')}>
                    Approve
                  </button>
                  <button className="text-xs px-2 py-1 rounded bg-red-50 text-red-700" onClick={() => moderateRecipe(recipe.id, 'reject')}>
                    Reject
                  </button>
                  <button className="text-xs px-2 py-1 rounded bg-amber-50 text-amber-700" onClick={() => moderateRecipe(recipe.id, 'flag')}>
                    Flag
                  </button>
                  <button className="text-xs text-blue-700 underline" onClick={() => setSelected(recipe)}>
                    Open
                  </button>
                </div>
              </div>
            ))}
            {!moderationQueue.length && <p className="text-sm text-gray-600">No recipes need moderation right now.</p>}
          </div>
        </div>
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
                <div className="text-xs text-gray-600">
                  Rating: {Number(selected.rating_avg || 0).toFixed(2)} ({selected.rating_count || 0}) | Moderation: {selected.moderation_status || 'approved'} | Verified: {selected.is_verified ? 'Yes' : 'No'}
                </div>
                <div className="text-xs text-gray-600">
                  Fiber: {Number(selected.nutrition?.fiber_g || 0).toFixed(1)}g | Sugar: {Number(selected.nutrition?.sugar_g || 0).toFixed(1)}g | Sodium: {Number(selected.nutrition?.sodium_mg || 0).toFixed(1)}mg
                </div>
                <div className="border rounded p-3 bg-gray-50 text-xs text-gray-700 space-y-1">
                  <div className="font-semibold text-gray-900">Advanced Nutrition Profile</div>
                  <div>
                    Glycemic Index: {Number(selected.nutrition?.glycemic_index || 0).toFixed(0)} | Satiety Index: {Number(selected.nutrition?.satiety_index || 0).toFixed(0)}
                  </div>
                  <div>
                    Nutrient Density Score: {Number(selected.nutrition?.nutrient_density_score || 0).toFixed(2)} | Processing Level: {selected.nutrition?.processing_level || 'n/a'}
                  </div>
                  <div>
                    Antioxidants - Polyphenols: {selected.nutrition?.antioxidant_profile?.polyphenols || 'n/a'},
                    Flavonoids: {selected.nutrition?.antioxidant_profile?.flavonoids || 'n/a'},
                    Carotenoids: {selected.nutrition?.antioxidant_profile?.carotenoids || 'n/a'}
                  </div>
                  <div>
                    Environmental Impact - Carbon: {selected.nutrition?.environmental_impact?.carbon_footprint || 'n/a'},
                    Water: {selected.nutrition?.environmental_impact?.water_usage || 'n/a'}
                  </div>
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
                  <label className="text-sm text-gray-700 block mb-1">Available ingredients for substitution</label>
                  <input
                    value={availableIngredientsInput}
                    onChange={(e) => setAvailableIngredientsInput(e.target.value)}
                    className="border rounded p-2 w-full text-sm"
                    placeholder="comma separated, e.g. tofu, lentils, quinoa"
                  />
                </div>
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
