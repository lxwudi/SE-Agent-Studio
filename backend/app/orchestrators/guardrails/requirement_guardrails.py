from app.orchestrators.outputs.requirement_models import RequirementSpec


def validate_requirement_spec(spec: RequirementSpec) -> None:
    if not spec.project_name.strip():
        raise ValueError("RequirementSpec.project_name is required.")
    if not spec.core_features:
        raise ValueError("RequirementSpec.core_features cannot be empty.")
    if any("无法确定" in item or "未提供" in item for item in spec.core_features):
        raise ValueError("RequirementSpec.core_features contains placeholder content.")
