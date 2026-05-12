"""Initial migration with pgvector extension and all tables

Revision ID: 001_initial
Revises:
Create Date: 2024-05-09 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create ingredients table
    op.create_table(
        'ingredients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('common_unit', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ingredients_id'), 'ingredients', ['id'], unique=False)
    op.create_index(op.f('ix_ingredients_name'), 'ingredients', ['name'], unique=True)
    op.create_index(op.f('ix_ingredients_category'), 'ingredients', ['category'], unique=False)

    # Create recipes table
    op.create_table(
        'recipes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cuisine', sa.String(length=100), nullable=True),
        sa.Column('meal_type', sa.String(length=50), nullable=True),
        sa.Column('difficulty', sa.String(length=50), nullable=True),
        sa.Column('prep_time', sa.Integer(), nullable=True),
        sa.Column('cook_time', sa.Integer(), nullable=True),
        sa.Column('total_time', sa.Integer(), nullable=True),
        sa.Column('servings', sa.Integer(), nullable=True),
        sa.Column('instructions', sa.JSON(), nullable=True),
        sa.Column('nutrition', sa.JSON(), nullable=True),
        sa.Column('dietary_tags', sa.JSON(), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('source', sa.String(length=200), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recipes_id'), 'recipes', ['id'], unique=False)
    op.create_index(op.f('ix_recipes_name'), 'recipes', ['name'], unique=False)
    op.create_index(op.f('ix_recipes_cuisine'), 'recipes', ['cuisine'], unique=False)

    # Create recipe_ingredients association table
    op.create_table(
        'recipe_ingredients',
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('preparation', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('recipe_id', 'ingredient_id')
    )

    # Create user_preferences table
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=200), nullable=False),
        sa.Column('dietary_restrictions', sa.JSON(), nullable=True),
        sa.Column('cuisine_preferences', sa.JSON(), nullable=True),
        sa.Column('allergies', sa.JSON(), nullable=True),
        sa.Column('disliked_ingredients', sa.JSON(), nullable=True),
        sa.Column('max_cooking_time', sa.Integer(), nullable=True),
        sa.Column('skill_level', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_preferences_id'), 'user_preferences', ['id'], unique=False)
    op.create_index(op.f('ix_user_preferences_user_id'), 'user_preferences', ['user_id'], unique=True)

    # Create agent_runs table
    op.create_table(
        'agent_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.String(length=200), nullable=False),
        sa.Column('agent_type', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('output_data', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('estimated_cost', sa.Float(), nullable=True),
        sa.Column('langsmith_trace_id', sa.String(length=200), nullable=True),
        sa.Column('otel_trace_id', sa.String(length=200), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_runs_id'), 'agent_runs', ['id'], unique=False)
    op.create_index(op.f('ix_agent_runs_run_id'), 'agent_runs', ['run_id'], unique=True)
    op.create_index(op.f('ix_agent_runs_agent_type'), 'agent_runs', ['agent_type'], unique=False)
    op.create_index(op.f('ix_agent_runs_user_id'), 'agent_runs', ['user_id'], unique=False)
    op.create_index(op.f('ix_agent_runs_status'), 'agent_runs', ['status'], unique=False)

    # Create menus table
    op.create_table(
        'menus',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=200), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('days_count', sa.Integer(), nullable=False),
        sa.Column('agent_run_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_menus_id'), 'menus', ['id'], unique=False)
    op.create_index(op.f('ix_menus_user_id'), 'menus', ['user_id'], unique=False)

    # Create menu_days table
    op.create_table(
        'menu_days',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('menu_id', sa.Integer(), nullable=False),
        sa.Column('day_number', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('meals', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['menu_id'], ['menus.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_menu_days_id'), 'menu_days', ['id'], unique=False)
    op.create_index(op.f('ix_menu_days_menu_id'), 'menu_days', ['menu_id'], unique=False)

    # Create grocery_lists table
    op.create_table(
        'grocery_lists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('menu_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('items', sa.JSON(), nullable=False),
        sa.Column('estimated_cost', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['menu_id'], ['menus.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_grocery_lists_id'), 'grocery_lists', ['id'], unique=False)
    op.create_index(op.f('ix_grocery_lists_menu_id'), 'grocery_lists', ['menu_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_grocery_lists_menu_id'), table_name='grocery_lists')
    op.drop_index(op.f('ix_grocery_lists_id'), table_name='grocery_lists')
    op.drop_table('grocery_lists')

    op.drop_index(op.f('ix_menu_days_menu_id'), table_name='menu_days')
    op.drop_index(op.f('ix_menu_days_id'), table_name='menu_days')
    op.drop_table('menu_days')

    op.drop_index(op.f('ix_menus_user_id'), table_name='menus')
    op.drop_index(op.f('ix_menus_id'), table_name='menus')
    op.drop_table('menus')

    op.drop_index(op.f('ix_agent_runs_status'), table_name='agent_runs')
    op.drop_index(op.f('ix_agent_runs_user_id'), table_name='agent_runs')
    op.drop_index(op.f('ix_agent_runs_agent_type'), table_name='agent_runs')
    op.drop_index(op.f('ix_agent_runs_run_id'), table_name='agent_runs')
    op.drop_index(op.f('ix_agent_runs_id'), table_name='agent_runs')
    op.drop_table('agent_runs')

    op.drop_index(op.f('ix_user_preferences_user_id'), table_name='user_preferences')
    op.drop_index(op.f('ix_user_preferences_id'), table_name='user_preferences')
    op.drop_table('user_preferences')

    op.drop_table('recipe_ingredients')

    op.drop_index(op.f('ix_recipes_cuisine'), table_name='recipes')
    op.drop_index(op.f('ix_recipes_name'), table_name='recipes')
    op.drop_index(op.f('ix_recipes_id'), table_name='recipes')
    op.drop_table('recipes')

    op.drop_index(op.f('ix_ingredients_category'), table_name='ingredients')
    op.drop_index(op.f('ix_ingredients_name'), table_name='ingredients')
    op.drop_index(op.f('ix_ingredients_id'), table_name='ingredients')
    op.drop_table('ingredients')

    # Drop pgvector extension
    op.execute('DROP EXTENSION IF EXISTS vector')