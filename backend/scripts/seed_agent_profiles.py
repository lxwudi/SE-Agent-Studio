from __future__ import annotations

from app.db.session import SessionLocal
from app.services.bootstrap_service import BootstrapService


def main() -> None:
    with SessionLocal() as session:
        BootstrapService.seed_defaults(session)
        session.commit()


if __name__ == "__main__":
    main()
