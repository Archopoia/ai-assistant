import React, { useEffect, useMemo, useState } from 'react';
import { useMealPlans, useShoppingList } from '../../hooks/useMealPlanning';
import { SHOPPING_CATEGORIES } from '../../utils/constants';

export const ShoppingListPage: React.FC = () => {
  const { plans, loading: plansLoading } = useMealPlans();
  const [selectedPlanId, setSelectedPlanId] = useState<number | undefined>(undefined);
  const [updatingItem, setUpdatingItem] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { list, loading, generate, updateItem } = useShoppingList(selectedPlanId);

  useEffect(() => {
    if (!selectedPlanId && plans.length > 0) {
      setSelectedPlanId(plans[0].id);
    }
  }, [plans, selectedPlanId]);

  useEffect(() => {
    if (selectedPlanId) {
      generate();
    }
  }, [selectedPlanId]);

  const categoryLabelMap = useMemo(
    () =>
      SHOPPING_CATEGORIES.reduce<Record<string, string>>((acc, key) => {
        acc[key] = key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        return acc;
      }, {}),
    []
  );

  const selectedPlan = useMemo(() => plans.find((plan) => plan.id === selectedPlanId), [plans, selectedPlanId]);

  const categorized = useMemo(() => {
    const buckets: Record<string, any[]> = {};
    if (!list) return buckets;
    for (const item of list.items) {
      if (!buckets[item.category]) buckets[item.category] = [];
      buckets[item.category].push(item);
    }
    return buckets;
  }, [list]);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Shopping List</h1>
      <div className="bg-white rounded-lg shadow-md p-6 space-y-4">
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-700">Meal plan</label>
          <select
            className="border rounded p-2"
            value={selectedPlanId || ''}
            onChange={(e) => setSelectedPlanId(Number(e.target.value))}
          >
            {plans.map((plan) => (
              <option key={plan.id} value={plan.id}>
                #{plan.id} - {plan.target_date} ({plan.duration})
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={async () => {
            await generate();
            setMessage('Shopping list refreshed.');
          }}
          className="px-3 py-2 rounded bg-indigo-600 text-white text-sm"
        >
          Regenerate List
        </button>
        <p className="text-sm text-gray-600">
          Items are grouped into meaningful categories. You can adjust quantities or exclude ingredients.
        </p>
        {selectedPlan && (
          <p className="text-sm text-gray-700">
            Showing {list?.items.length || 0} items for plan #{selectedPlan.id} on {selectedPlan.target_date} ({selectedPlan.duration}).
          </p>
        )}
        {message && <p className="text-sm text-green-700">{message}</p>}
      </div>

      {(loading || plansLoading) && <p className="text-gray-600">Loading shopping list...</p>}
      {!loading && list && (
        <div className="space-y-4">
          {Object.entries(categorized).map(([category, items]) => (
            <div key={category} className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3 capitalize">{categoryLabelMap[category] || category.replace(/_/g, ' ')}</h2>
              <div className="space-y-2">
                {items.map((item) => (
                  <div key={item.name} className="grid grid-cols-1 md:grid-cols-5 gap-2 items-center border rounded p-3">
                    <div className="text-sm text-gray-900">
                      <div>{item.name}</div>
                      {item.used_in && item.used_in.length > 0 && (
                        <div className="text-xs text-gray-500">Used in: {item.used_in.join(', ')}</div>
                      )}
                    </div>
                    <div className="text-sm text-gray-600">{item.unit}</div>
                    <input
                      type="number"
                      value={item.quantity}
                      onChange={async (e) => {
                        try {
                          setError(null);
                          setUpdatingItem(item.name);
                          await updateItem(item.name, Number(e.target.value), item.excluded);
                          setMessage(`Updated ${item.name}.`);
                        } catch (err: any) {
                          setError(err?.response?.data?.detail || err?.message || 'Failed to update item');
                        } finally {
                          setUpdatingItem(null);
                        }
                      }}
                      className="border rounded p-1"
                    />
                    <label className="text-sm text-gray-700 flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={item.excluded}
                        onChange={async () => {
                          const nextExcluded = !item.excluded;
                          try {
                            setError(null);
                            setUpdatingItem(item.name);
                            await updateItem(item.name, item.quantity, nextExcluded);
                            setMessage(`${nextExcluded ? 'Excluded' : 'Included'} ${item.name}.`);
                          } catch (err: any) {
                            setError(err?.response?.data?.detail || err?.message || 'Failed to update item');
                          } finally {
                            setUpdatingItem(null);
                          }
                        }}
                      />
                      Exclude
                    </label>
                    <div className="text-xs text-gray-500">{updatingItem === item.name ? 'Updating...' : ''}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
};
