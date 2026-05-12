# Recipe AI System - Frontend

Next.js frontend application for the Recipe AI System, providing an intuitive interface for AI-powered recipe recommendations.

## Tech Stack

- **Next.js 15** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **React** - UI library

## Project Structure

```
apps/web/
├── app/
│   ├── layout.tsx          # Root layout with metadata
│   ├── page.tsx            # Home page with recipe form
│   ├── globals.css         # Global styles and Tailwind
│   └── favicon.ico         # Favicon
├── public/                 # Static assets
├── node_modules/           # Dependencies
├── package.json            # Project dependencies
├── tsconfig.json           # TypeScript configuration
├── tailwind.config.ts      # Tailwind CSS configuration
└── README.md              # This file
```

## Getting Started

### Prerequisites

- Node.js 18 or higher
- npm, yarn, pnpm, or bun

### Installation

1. **Navigate to the web directory:**
   ```bash
   cd apps/web
   ```

2. **Install dependencies:**
   ```bash
   npm install
   # or
   yarn install
   # or
   pnpm install
   ```

### Running the Development Server

Start the development server:

```bash
npm run dev
```

The application will be available at:
- **Frontend**: http://localhost:3000

The page will automatically reload when you make changes to the code.

### Available Scripts

- `npm run dev` - Start development server on port 3000
- `npm run build` - Build the application for production
- `npm run start` - Start the production server
- `npm run lint` - Run ESLint for code linting
- `npm run type-check` - Run TypeScript type checking

## Features

### Current Features

The application currently includes:

1. **Recipe Recommendation Form**
   - Available ingredients input (textarea)
   - Dietary restrictions selector (multi-select buttons)
   - Cuisine preferences selector (multi-select buttons)
   - Number of days slider (1-7 days)
   - Submit button for generating recommendations

2. **User Interface**
   - Clean, modern design with Tailwind CSS
   - Responsive layout (mobile-first)
   - Dark mode support
   - Interactive form elements with visual feedback

### Form Fields

#### Available Ingredients
Free-text input where users can list all ingredients they have available, separated by commas.

#### Dietary Restrictions
Multi-select options:
- Vegetarian
- Vegan
- Gluten-Free
- Dairy-Free
- Nut-Free
- Keto
- Paleo

#### Cuisine Preferences
Multi-select options:
- Italian
- Mexican
- Asian
- Mediterranean
- American
- Indian
- French
- Thai

#### Number of Days
Slider input (1-7 days) for meal plan duration.

## API Integration (Coming Soon)

The form is currently a placeholder. API integration will be added to:
- Submit form data to the FastAPI backend
- Display AI-generated recipe recommendations
- Show loading states during processing
- Handle errors gracefully

## Development

### Project Conventions

- **TypeScript**: All components use TypeScript for type safety
- **"use client"**: Client components marked for interactivity
- **Tailwind CSS**: Utility-first styling approach
- **Component Structure**: Functional components with hooks

### Adding New Pages

Create new pages in the `app` directory:

```typescript
// app/recipes/page.tsx
export default function RecipesPage() {
  return <div>Recipes</div>;
}
```

Routes are automatically created based on folder structure.

### Styling Guidelines

- Use Tailwind CSS utility classes
- Follow dark mode conventions with `dark:` prefix
- Maintain responsive design with breakpoint prefixes (`sm:`, `md:`, `lg:`)
- Use consistent color scheme (indigo/blue palette)

### TypeScript

Type your components and props:

```typescript
interface ButtonProps {
  label: string;
  onClick: () => void;
}

export function Button({ label, onClick }: ButtonProps) {
  return <button onClick={onClick}>{label}</button>;
}
```

## Building for Production

To create an optimized production build:

```bash
npm run build
```

To run the production build locally:

```bash
npm run start
```

## Environment Variables

Create a `.env.local` file for environment variables:

```env
NEXT_PUBLIC_API_URL=http://localhost:4000
```

Variables prefixed with `NEXT_PUBLIC_` are available in the browser.

## Troubleshooting

### Port Already in Use

If port 3000 is already in use:

```bash
# Find and kill the process
lsof -ti:3000 | xargs kill -9

# Or run on a different port
PORT=3001 npm run dev
```

### Module Not Found

Clear cache and reinstall dependencies:

```bash
rm -rf node_modules .next
npm install
npm run dev
```

### Type Errors

Run type checking to identify issues:

```bash
npm run type-check
```

## Next Steps

Planned features and improvements:

- [ ] Connect to FastAPI backend
- [ ] Display recipe recommendations
- [ ] Add recipe detail pages
- [ ] Implement recipe search functionality
- [ ] Add user authentication
- [ ] Create meal planning calendar view
- [ ] Add favorite recipes feature
- [ ] Implement recipe sharing
- [ ] Add nutrition information display

## Additional Resources

- [Next.js Documentation](https://nextjs.org/docs) - Next.js features and API
- [Next.js App Router](https://nextjs.org/docs/app) - App Router documentation
- [Tailwind CSS](https://tailwindcss.com/docs) - Tailwind CSS documentation
- [TypeScript](https://www.typescriptlang.org/docs) - TypeScript documentation
- [React](https://react.dev) - React documentation

## Contributing

When contributing to the frontend:

1. Follow TypeScript best practices
2. Use Tailwind CSS for styling
3. Ensure responsive design (mobile-first)
4. Test on multiple screen sizes
5. Run linting before committing: `npm run lint`
6. Ensure type safety: `npm run type-check`

## License

See [LICENSE](../../LICENSE) file in the project root for details.