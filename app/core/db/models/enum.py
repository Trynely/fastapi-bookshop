from alembic import op

def create_enum(enum):
    enum.create(op.get_bind(), checkfirst=True)

def drop_enum(enum):
    enum.drop(op.get_bind(), checkfirst=True)