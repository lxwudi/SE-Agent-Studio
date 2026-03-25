from app.db.session import session_scope
from app.services.bootstrap_service import bootstrap_catalog


def main() -> None:
    with session_scope() as db:
        bootstrap_catalog(db)
    print("Bootstrap completed. Make sure database migrations have already been applied.")


if __name__ == "__main__":
    main()
