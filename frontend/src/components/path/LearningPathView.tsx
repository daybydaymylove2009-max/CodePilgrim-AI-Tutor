import { useEffect, useState } from "react";
import { useLearningStore } from "../../store";
import { knowledgeApi } from "../../api";
import type { LearningPathNode } from "../../types";
import { Lock, CheckCircle, Circle, Play, ChevronRight } from "lucide-react";

const MASTERY_COLORS: Record<string, string> = {
  unlearned: "#94a3b8",
  weak: "#f97316",
  surface: "#eab308",
  learned: "#22c55e",
  mastered: "#6366f1",
};

const MASTERY_LABELS: Record<string, string> = {
  unlearned: "未学习",
  weak: "薄弱",
  surface: "表面理解",
  learned: "已掌握",
  mastered: "精通",
};

export default function LearningPathView() {
  const { learningPath, loadLearningPath, currentKpId, setCurrentKpId } = useLearningStore();
  const [kpDetails, setKpDetails] = useState<Record<string, string>>({});

  useEffect(() => {
    loadLearningPath();
  }, []);

  useEffect(() => {
    if (learningPath) {
      const fetchDetails = async () => {
        const details: Record<string, string> = {};
        for (const node of learningPath.nodes) {
          try {
            const { data } = await knowledgeApi.getPoint(node.kp_id);
            details[node.kp_id] = data.description || "";
          } catch {
            details[node.kp_id] = "";
          }
        }
        setKpDetails(details);
      };
      fetchDetails();
    }
  }, [learningPath]);

  if (!learningPath) {
    return <div className="loading">加载学习路径中...</div>;
  }

  const progress = learningPath.total_kps > 0
    ? Math.round((learningPath.mastered_count / learningPath.total_kps) * 100)
    : 0;

  return (
    <div className="learning-path">
      <div className="path-header">
        <h2>学习路径</h2>
        <div className="progress-bar-container">
          <div className="progress-bar" style={{ width: `${progress}%` }} />
          <span className="progress-text">{progress}% 完成</span>
        </div>
        <p className="progress-detail">
          已掌握 {learningPath.mastered_count} / {learningPath.total_kps} 个知识点
        </p>
      </div>

      <div className="path-nodes">
        {learningPath.nodes.map((node: LearningPathNode) => (
          <PathNodeCard
            key={node.kp_id}
            node={node}
            description={kpDetails[node.kp_id] || ""}
            isCurrent={node.kp_id === currentKpId}
            onSelect={() => setCurrentKpId(node.kp_id)}
          />
        ))}
      </div>
    </div>
  );
}

function PathNodeCard({
  node,
  description,
  isCurrent,
  onSelect,
}: {
  node: LearningPathNode;
  description: string;
  isCurrent: boolean;
  onSelect: () => void;
}) {
  const masteryColor = MASTERY_COLORS[node.mastery_level] || "#94a3b8";
  const masteryLabel = MASTERY_LABELS[node.mastery_level] || node.mastery_level;

  return (
    <div
      className={`path-node ${isCurrent ? "current" : ""} ${!node.is_unlocked ? "locked" : ""}`}
      onClick={node.is_unlocked ? onSelect : undefined}
    >
      <div className="node-icon">
        {!node.is_unlocked ? (
          <Lock size={20} />
        ) : node.mastery_level === "mastered" || node.mastery_level === "learned" ? (
          <CheckCircle size={20} color={masteryColor} />
        ) : isCurrent ? (
          <Play size={20} color="#6366f1" />
        ) : (
          <Circle size={20} color={masteryColor} />
        )}
      </div>

      <div className="node-content">
        <div className="node-title">
          <span>{node.title}</span>
          <span className="mastery-badge" style={{ backgroundColor: masteryColor }}>
            {masteryLabel}
          </span>
        </div>
        {description && <p className="node-desc">{description.length > 150 ? description.slice(0, 150) + "..." : description}</p>}
        <div className="node-meta">
          <span className="difficulty">难度: {"★".repeat(node.difficulty)}{"☆".repeat(5 - node.difficulty)}</span>
          <span className="bkt-score">掌握度: {Math.round(node.bkt_p_know * 100)}%</span>
        </div>
      </div>

      {node.is_unlocked && (
        <div className="node-action">
          <ChevronRight size={18} />
        </div>
      )}
    </div>
  );
}
