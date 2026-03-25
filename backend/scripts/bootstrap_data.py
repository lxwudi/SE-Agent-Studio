from app.db.session import create_all_tables, session_scope
from app.services.bootstrap_service import bootstrap_catalog


def main() -> None:
    create_all_tables()
    with session_scope() as db:
        bootstrap_catalog(db)
    print("Bootstrap completed.")


if __name__ == "__main__":
    main()
