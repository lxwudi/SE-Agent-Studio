const stageLabels: Record<string, string> = {
  created: "已创建",
  queued: "等待开始",
  requirements: "需求梳理",
  architecture: "架构设计",
  backend_design: "后端方案",
  frontend_design: "前端方案",
  ai_design: "AI 集成",
  quality_assurance: "测试方案",
  consistency_review: "综合复核",
  completed: "已完成",
};

const artifactTypeLabels: Record<string, string> = {
  requirement_spec: "需求说明",
  architecture_blueprint: "架构蓝图",
  backend_design: "后端设计",
  frontend_blueprint: "前端设计",
  ai_integration_spec: "AI 集成方案",
  api_test_plan: "测试计划",
  review_summary: "复核结论",
};

const agentLabels: Record<string, string> = {
  product_manager: "产品经理",
  software_architect: "软件架构师",
  backend_architect: "后端架构师",
  frontend_developer: "前端工程师",
  ai_engineer: "AI 工程师",
  api_tester: "测试工程师",
};

const eventSourceLabels: Record<string, string> = {
  TechnicalDesignFlow: "设计流程",
  RunService: "运行控制",
  RequirementAnalysisCrew: "需求分析",
  ArchitectureDesignCrew: "架构设计",
  BackendDesignCrew: "后端设计",
  FrontendDesignCrew: "前端设计",
  AIPlatformDesignCrew: "AI 集成设计",
  QualityAssuranceCrew: "测试设计",
  ConsistencyReviewCrew: "结果复核",
};

const eventTypeLabels: Record<string, string> = {
  "flow.started": "任务已启动",
  "flow.cancel_requested": "已请求取消",
  "flow.completed": "任务已完成",
  "flow.cancelled": "任务已取消",
  "task.started": "阶段开始",
  "task.completed": "阶段完成",
  "task.cancelled": "阶段已取消",
  "task.failed": "阶段失败",
};

const statusLabels: Record<string, string> = {
  COMPLETED: "已完成",
  SUCCEEDED: "已完成",
  RUNNING: "进行中",
  QUEUED: "等待中",
  CREATED: "已创建",
  WAITING_REVIEW: "待确认",
  RETRYING: "重试中",
  FAILED: "失败",
  PARTIAL_FAILED: "部分失败",
  CANCELLED: "已取消",
  SKIPPED: "已跳过",
};

export function getStageLabel(stage: string) {
  return stageLabels[stage] ?? stage;
}

export function getStageDescription(stage: string) {
  const descriptions: Record<string, string> = {
    requirements: "提炼项目目标、范围和约束条件",
    architecture: "梳理系统结构、模块关系和关键决策",
    backend_design: "规划服务接口、数据模型和后端能力",
    frontend_design: "设计页面结构、交互流程和组件方案",
    ai_design: "确定模型调用方式、提示策略和安全边界",
    quality_assurance: "补齐测试策略、场景覆盖和验收要点",
    consistency_review: "统一复核各部分方案是否一致",
    completed: "全部设计文档已生成并归档",
  };
  return descriptions[stage] ?? "等待该阶段开始执行";
}

export function getArtifactTypeLabel(type: string) {
  return artifactTypeLabels[type] ?? type;
}

export function getAgentLabel(agentCode: string) {
  return agentLabels[agentCode] ?? agentCode;
}

export function getEventSourceLabel(source: string) {
  return eventSourceLabels[source] ?? source;
}

export function getEventTypeLabel(type: string) {
  return eventTypeLabels[type] ?? type;
}

export function getStatusLabel(status: string) {
  return statusLabels[status] ?? status;
}
