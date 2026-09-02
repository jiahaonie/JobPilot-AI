from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import Settings
from app.models import Base

# 迁移工具配置对象，用于访问当前 .ini 文件中的配置值。
config = context.config

# 读取配置文件并初始化 Python 日志器。
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = Settings().database_url
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = Base.metadata


def _configure_context(**kwargs: object) -> None:
    """应用 SQLite 与后续数据库共用的模型比较选项。"""
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=database_url.startswith("sqlite"),
        **kwargs,
    )


def run_migrations_offline() -> None:
    """以离线模式运行迁移，仅通过数据库地址生成迁移脚本。"""
    url = config.get_main_option("sqlalchemy.url")
    _configure_context(
        url=url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """以在线模式运行迁移，并将数据库连接绑定到迁移上下文。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _configure_context(connection=connection)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
