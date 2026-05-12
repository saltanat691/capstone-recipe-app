"""
Script to verify database setup and connection.
"""

import asyncio
from sqlalchemy import text

from app.db.session import engine
from app.models import Recipe, Ingredient, UserPreference, Menu, AgentRun


async def verify_database():
    """
    Verify database connection and check that all tables exist.
    """
    print("Verifying database setup...")
    print("-" * 50)

    try:
        async with engine.connect() as conn:
            # Check connection
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✓ PostgreSQL connected: {version[:50]}...")

            # Check pgvector extension
            result = await conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )
            if result.scalar():
                print("✓ pgvector extension is enabled")
            else:
                print("✗ pgvector extension is NOT enabled")

            # Check tables
            tables = [
                "recipes",
                "ingredients",
                "recipe_ingredients",
                "user_preferences",
                "menus",
                "menu_days",
                "grocery_lists",
                "agent_runs",
            ]

            for table in tables:
                result = await conn.execute(
                    text(
                        f"SELECT EXISTS (SELECT FROM information_schema.tables "
                        f"WHERE table_name = '{table}')"
                    )
                )
                exists = result.scalar()
                status = "✓" if exists else "✗"
                print(f"{status} Table '{table}' {'exists' if exists else 'NOT found'}")

            # Count records
            print("\n" + "-" * 50)
            print("Record counts:")
            for table in tables:
                try:
                    result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"  {table}: {count} records")
                except Exception:
                    pass

    except Exception as e:
        print(f"✗ Error connecting to database: {e}")
        return False

    print("\n" + "-" * 50)
    print("✓ Database verification complete!")
    return True


if __name__ == "__main__":
    asyncio.run(verify_database())