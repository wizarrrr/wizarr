"""fix_password_reset_token_cascade_delete

Revision ID: c854ad44aad5
Revises: a052ac2ce6a9
Create Date: 2025-11-21 01:35:28.015267

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c854ad44aad5'
down_revision = 'a052ac2ce6a9'
branch_labels = None
depends_on = None


def upgrade():
    """Fix password_reset_token foreign key to properly cascade delete."""
    # SQLite doesn't support altering foreign keys, so we need to recreate the table
    connection = op.get_bind()
    
    # Disable foreign keys temporarily
    connection.execute(sa.text("PRAGMA foreign_keys = OFF"))
    
    # Create new table with correct foreign key constraint
    op.create_table(
        'password_reset_token_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    
    # Copy data from old table to new table
    connection.execute(sa.text("""
        INSERT INTO password_reset_token_new 
        (id, code, user_id, created_at, expires_at, used, used_at)
        SELECT id, code, user_id, created_at, expires_at, used, used_at
        FROM password_reset_token
    """))
    
    # Drop old table
    op.drop_table('password_reset_token')
    
    # Rename new table to original name
    op.rename_table('password_reset_token_new', 'password_reset_token')
    
    # Re-enable foreign keys
    connection.execute(sa.text("PRAGMA foreign_keys = ON"))


def downgrade():
    """Revert to previous foreign key constraint (non-cascading)."""
    connection = op.get_bind()
    
    # Disable foreign keys temporarily
    connection.execute(sa.text("PRAGMA foreign_keys = OFF"))
    
    # Create old table structure (without CASCADE)
    op.create_table(
        'password_reset_token_old',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    
    # Copy data back
    connection.execute(sa.text("""
        INSERT INTO password_reset_token_old 
        (id, code, user_id, created_at, expires_at, used, used_at)
        SELECT id, code, user_id, created_at, expires_at, used, used_at
        FROM password_reset_token
    """))
    
    # Drop current table
    op.drop_table('password_reset_token')
    
    # Rename old table back
    op.rename_table('password_reset_token_old', 'password_reset_token')
    
    # Re-enable foreign keys
    connection.execute(sa.text("PRAGMA foreign_keys = ON"))
