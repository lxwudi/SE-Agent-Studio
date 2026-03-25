from app.orchestrators.outputs.architecture_models import ArchitectureBlueprint


def validate_architecture_blueprint(blueprint: ArchitectureBlueprint) -> None:
    if not blueprint.architecture_style.strip():
        raise ValueError("ArchitectureBlueprint.architecture_style is required.")
    if not blueprint.core_modules:
        raise ValueError("ArchitectureBlueprint.core_modules cannot be empty.")
