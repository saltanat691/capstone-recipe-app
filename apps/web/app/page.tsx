"use client";

import { useState, FormEvent } from "react";

export default function Home() {
  const [ingredients, setIngredients] = useState("");
  const [dietaryRestrictions, setDietaryRestrictions] = useState<string[]>([]);
  const [cuisinePreferences, setCuisinePreferences] = useState<string[]>([]);
  const [numberOfDays, setNumberOfDays] = useState(1);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    // TODO: API integration will be added later
    console.log({
      ingredients,
      dietaryRestrictions,
      cuisinePreferences,
      numberOfDays,
    });
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
            {/* Available Ingredients */}
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
              />
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                List all ingredients you have available
              </p>
            </div>

            {/* Dietary Restrictions */}
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
                    className={`px-4 py-2 rounded-lg border-2 transition-all duration-200 ${
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

            {/* Cuisine Preferences */}
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
                    className={`px-4 py-2 rounded-lg border-2 transition-all duration-200 ${
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

            {/* Number of Days */}
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
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
                />
                <span className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 min-w-[3rem] text-center">
                  {numberOfDays}
                </span>
              </div>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                Generate meal plans for {numberOfDays}{" "}
                {numberOfDays === 1 ? "day" : "days"}
              </p>
            </div>

            {/* Submit Button */}
            <div className="pt-4">
              <button
                type="submit"
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-4 px-6 rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-[1.02]"
              >
                Generate Recipe Recommendations
              </button>
            </div>
          </form>
        </div>

        {/* Info Footer */}
        <div className="mt-8 text-center">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Powered by AI agents with LangGraph orchestration
          </p>
        </div>
      </main>
    </div>
  );
}