import type {
  Artifact,
  DeliveryCommandSpec,
  DeliveryGeneratedFile,
  DeliveryVerificationResult,
} from "../types";


const artifactPriority: Record<string, number> = {
  delivery_handoff: 0,
  integration_bundle: 1,
  backend_code_bundle: 2,
  frontend_code_bundle: 3,
  solution_delivery_plan: 4,
  delivery_requirements: 5,
};

export function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
}

export function sortArtifactsByPriority(artifacts: Artifact[]) {
  return [...artifacts].sort((left, right) => {
    const leftPriority = artifactPriority[left.artifact_type] ?? 99;
    const rightPriority = artifactPriority[right.artifact_type] ?? 99;
    if (leftPriority !== rightPriority) {
      return leftPriority - rightPriority;
    }

    if (left.version_no !== right.version_no) {
      return right.version_no - left.version_no;
    }

    return Date.parse(right.created_at) - Date.parse(left.created_at);
  });
}

export function getPreferredArtifact(artifacts: Artifact[]) {
  return sortArtifactsByPriority(artifacts)[0] ?? null;
}

export function extractStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

export function extractFirstStringList(content: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const extracted = extractStringList(content[key]);
    if (extracted.length) {
      return extracted;
    }
  }
  return [] as string[];
}

export function extractCommandSpecs(value: unknown): DeliveryCommandSpec[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    .map((item) => ({
      label: typeof item.label === "string" ? item.label : "未命名命令",
      command: typeof item.command === "string" ? item.command : "",
      purpose: typeof item.purpose === "string" ? item.purpose : "",
    }))
    .filter((item) => item.command);
}

export function extractFirstCommandList(content: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const extracted = extractCommandSpecs(content[key]);
    if (extracted.length) {
      return extracted;
    }
  }
  return [] as DeliveryCommandSpec[];
}

export function extractGeneratedFiles(value: unknown): DeliveryGeneratedFile[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    .map((item) => ({
      path: typeof item.path === "string" ? item.path : "unknown",
      language: typeof item.language === "string" ? item.language : "",
      purpose: typeof item.purpose === "string" ? item.purpose : "",
      content: typeof item.content === "string" ? item.content : "",
    }));
}

export function extractVerificationResults(value: unknown): DeliveryVerificationResult[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    .map((item) => ({
      label: typeof item.label === "string" ? item.label : "未命名检查",
      command: typeof item.command === "string" ? item.command : "",
      success: item.success === true,
      exit_code: typeof item.exit_code === "number" ? item.exit_code : -1,
      summary: typeof item.summary === "string" ? item.summary : "",
      output: typeof item.output === "string" ? item.output : "",
    }));
}

export function extractWorkspaceRoot(content: Record<string, unknown>) {
  const value = content.workspace_root;
  return typeof value === "string" ? value : "";
}
