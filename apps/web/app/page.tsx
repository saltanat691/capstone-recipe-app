"use client";

import { useState, FormEvent } from "react";

import {
  ApiError,
  fetchRecommendations,
  type RecommendationResponse,
} from "./lib/api";

export default function Home() {
  const [ingredients, setIngredients] = useState("");
  const [dietaryRestrictions, setDietaryRestrictions] = useState<string[]>([]);
  const [cuisinePreferences, setCuisinePreferences] = useState<string[]>([]);
  const [numberOfDays, setNumberOfDays] = useState(1);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RecommendationResponse | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);

    const availableIngredients = ingredients
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const restrictions = dietaryRestrictions.map((r) => r.toLowerCase());
    const cuisines = cuisinePreferences.map((c) => c.toLowerCase());

    const messageParts: string[] = [];
    if (numberOfDays > 1) {
      messageParts.push(`Create a ${numberOfDays}-day menu`);
    } else {
      messageParts.push("Suggest a recipe");
    }
    if (availableIngredients.length) {
      messageParts.push(`with ${availableIngredients.join(", ")}`);
    }
    if (restrictions.length) {
      messageParts.push(`(${restrictions.join(", ")})`);
    }
    if (cuisines.length) {
      messageParts.push(`prefer ${cuisines.join(", ")} cuisine`);
    }
    const message = messageParts.join(" ");

    try {
      const response = await fetchRecommendations({
        message,
        available_ingredients: availableIngredients,
        dietary_restrictions: restrictions,
        cuisine_preferences: cuisines,
        days: numberOfDays > 1 ? numberOfDays : null,
      });
      setResult(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`API error (${err.status}): ${err.body || "request failed"}`);
      } else if (err instanceof Error) {
        setError(`Network error: ${err.message}`);
      } else {
        setError("Unknown error contacting the API.");
      }
    } finally {
      setLoading(false);
    }
  };

  const toggleDietaryRestriction = (restriction: string) => {
    setDietaryRestrictions((prev) =>
      prev.includes(restriction)
        ? prev.filter((r) => r !== restriction)
        : [...prev, restriction]
    );
  };

  const toggleCuisinePreference = (cuisine: string) => {
    setCuisinePreferences((prev) =>
      prev.includes(cuisine)
        ? prev.filter((c) => c !== cuisine)
        : [...prev, cuisine]
    );
  };

  const dietaryOptions = [
    "Vegetarian",
    "Vegan",
    "Gluten-Free",
    "Dairy-Free",
    "Nut-Free",
    "Keto",
    "Paleo",
  ];

  const cuisineOptions = [
    "Italian",
    "Mexican",
    "Asian",
    "Mediterranean",
    "American",
    "Indian",
    "French",
    "Thai",
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <main className="container mx-auto px-4 py-12 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 dark:text-white mb-4">
            Recipe AI System
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300">
            AI-powered recipe recommendations tailored to your preferences
          </p>
        </div>

        {/* Form Card */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
          <form onSubmit={handleSubmit} className="space-y-8">
            <div>
              <label
                htmlFor="ingredients"
                className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2"
              >
                Available Ingredients
              </label>
              <textarea
                id="ingredients"
                rows={4}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent dark:bg-gray-700 dark:text-white transition"
                placeholder="Enter ingredients separated by commas (e.g., chicken, tomatoes, garlic, pasta)"
                value={ingredients}
                onChange={(e) => setIngredients(e.target.value)}
                disabled={loading}
              />
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                List all ingredients you have available
              </p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">
                Dietary Restrictions
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {dietaryOptions.map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => toggleDietaryRestriction(option)}
                    disabled={loading}
                    className={`px-4 py-2 rounded-lg border-2 transition-all duration-200 disabled:opacity-50 ${
                      dietaryRestrictions.includes(option)
                        ? "bg-indigo-600 border-indigo-600 text-white"
                        : "border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-indigo-400"
                    }`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">
                Cuisine Preferences
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {cuisineOptions.map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => toggleCuisinePreference(option)}
                    disabled={loading}
                    className={`px-4 py-2 rounded-lg border-2 transition-all duration-200 disabled:opacity-50 ${
                      cuisinePreferences.includes(option)
                        ? "bg-indigo-600 border-indigo-600 text-white"
                        : "border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-indigo-400"
                    }`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label
                htmlFor="days"
                className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2"
              >
                Number of Days
              </label>
              <div className="flex items-center space-x-4">
                <input
                  type="range"
                  id="days"
                  min="1"
                  max="7"
                  value={numberOfDays}
                  onChange={(e) => setNumberOfDays(parseInt(e.target.value))}
                  disabled={loading}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
                />
                <span className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 min-w-[3rem] text-center">
                  {numberOfDays}
                </span>
              </div>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                {numberOfDays === 1
                  ? "Recommendations only (no menu plan)"
                  : `Generate a ${numberOfDays}-day menu and grocery list`}
              </p>
            </div>

            <div className="pt-4">
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-4 px-6 rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-[1.02] disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
              >
                {loading
                  ? "Generating…"
                  : "Generate Recipe Recommendations"}
              </button>
            </div>
          </form>
        </div>

        {/* Loading skeleton */}
        {loading && (
          <div
            className="mt-8 bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 animate-pulse"
            aria-busy="true"
            aria-live="polite"
          >
            <div className="h-6 w-1/3 bg-gray-200 dark:bg-gray-700 rounded mb-4"></div>
            <div className="h-4 w-2/3 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
            <div className="h-4 w-1/2 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <div
            className="mt-8 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-red-800 dark:text-red-200"
            role="alert"
          >
            <p className="font-semibold mb-1">Could not generate recommendations</p>
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Result */}
        {result && !loading && <ResultView result={result} />}

        <div className="mt-8 text-center">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Powered by AI agents with LangGraph orchestration
          </p>
        </div>
      </main>
    </div>
  );
}

function ResultView({ result }: { result: RecommendationResponse }) {
  return (
    <div className="mt-8 space-y-6">
      {result.trace_id && (
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
          trace_id: <span className="font-mono">{result.trace_id}</span>
        </p>
      )}

      {result.warnings.length > 0 && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-6">
          <h3 className="font-semibold text-amber-900 dark:text-amber-200 mb-2">
            Warnings
          </h3>
          <ul className="list-disc list-inside text-sm text-amber-800 dark:text-amber-200 space-y-1">
            {result.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {result.nutrition_notes && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
            Nutrition notes
          </h3>
          <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-line">
            {result.nutrition_notes}
          </p>
        </div>
      )}

      {result.recommendations.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
            Recommended recipes ({result.recommendations.length})
          </h3>
          <ul className="space-y-4">
            {result.recommendations.map((rec, i) => (
              <li
                key={rec.id ?? i}
                className="border-l-4 border-indigo-500 pl-4"
              >
                <p className="font-medium text-gray-900 dark:text-white">
                  {rec.name}
                  {rec.cuisine && (
                    <span className="ml-2 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                      {rec.cuisine}
                    </span>
                  )}
                </p>
                {rec.ingredients && rec.ingredients.length > 0 && (
                  <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
                    Ingredients: {rec.ingredients.slice(0, 8).join(", ")}
                    {rec.ingredients.length > 8 ? "…" : ""}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.menu_plan && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
            Menu plan — {result.menu_plan.total_days} day(s),{" "}
            {result.menu_plan.servings} serving(s)/meal
          </h3>
          <ul className="space-y-3">
            {result.menu_plan.days.map((day) => (
              <li key={day.day} className="text-sm">
                <p className="font-medium text-gray-900 dark:text-white">
                  Day {day.day}
                  {day.date && (
                    <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                      {day.date}
                    </span>
                  )}
                </p>
                <ul className="ml-4 mt-1 text-gray-700 dark:text-gray-300">
                  {Object.entries(day.meals).map(([mealType, recipe]) => (
                    <li key={mealType}>
                      <span className="capitalize font-medium">
                        {mealType}:
                      </span>{" "}
                      {recipe.name}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.grocery_list && result.grocery_list.items.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
            Grocery list — {result.grocery_list.total_items} item(s)
          </h3>
          <div className="space-y-4">
            {Object.entries(result.grocery_list.categories).map(
              ([category, items]) => (
                <div key={category}>
                  <h4 className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
                    {category}
                  </h4>
                  <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-1">
                    {items.map((item, i) => (
                      <li
                        key={`${category}-${i}`}
                        className={
                          item.already_available
                            ? "text-gray-400 dark:text-gray-500 line-through"
                            : ""
                        }
                      >
                        {item.quantity != null && item.unit
                          ? `${item.quantity} ${item.unit} — `
                          : item.quantity != null
                          ? `${item.quantity} — `
                          : ""}
                        {item.ingredient}
                        {item.already_available && (
                          <span className="ml-2 text-xs uppercase tracking-wide text-green-600 dark:text-green-400 no-underline">
                            on hand
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )
            )}
          </div>
        </div>
      )}
    </div>
  );
}