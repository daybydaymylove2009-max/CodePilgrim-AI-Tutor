import { useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeTypes,
  Handle,
  Position,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { LearningPathNode } from "../../types";

const MASTERY_COLORS: Record<string, string> = {
  unlearned: "#94a3b8",
  weak: "#f97316",
  surface: "#eab308",
  learned: "#22c55e",
  mastered: "#6366f1",
};

const MASTERY_BG: Record<string, string> = {
  unlearned: "#1e293b",
  weak: "#431407",
  surface: "#422006",
  learned: "#052e16",
  mastered: "#1e1b4b",
};

function KnowledgeNode({ data }: NodeProps) {
  const { label, mastery, bktPknow, difficulty, isUnlocked, isCurrent } = data;
  const color = MASTERY_COLORS[mastery as string] || "#94a3b8";
  const bg = MASTERY_BG[mastery as string] || "#1e293b";

  return (
    <div
      className={`kp-node ${isCurrent ? "current" : ""} ${!isUnlocked ? "locked" : ""}`}
      style={{ borderColor: color, backgroundColor: bg }}
    >
      <Handle type="target" position={Position.Top} style={{ background: color }} />
      <div className="kp-node-header" style={{ borderBottomColor: color }}>
        <span className="kp-node-title">{label as string}</span>
        <span className="kp-node-badge" style={{ backgroundColor: color }}>
          {mastery as string}
        </span>
      </div>
      <div className="kp-node-body">
        <div className="kp-node-progress">
          <div className="kp-node-bar" style={{ width: `${(bktPknow as number) * 100}%`, backgroundColor: color }} />
        </div>
        <span className="kp-node-pct">{Math.round((bktPknow as number) * 100)}%</span>
        <span className="kp-node-diff">{"★".repeat(difficulty as number)}</span>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: color }} />
    </div>
  );
}

const nodeTypes: NodeTypes = {
  knowledgeNode: KnowledgeNode,
};

interface KnowledgeGraphProps {
  nodes: LearningPathNode[];
  currentKpId: string | null;
  onSelectKp: (kpId: string) => void;
}

export default function KnowledgeGraph({ nodes, currentKpId, onSelectKp }: KnowledgeGraphProps) {
  const flowNodes: Node[] = useMemo(() => {
    const topicGroups: Record<string, LearningPathNode[]> = {};
    nodes.forEach((n) => {
      if (!topicGroups[n.title]) topicGroups[n.title] = [];
      topicGroups[n.title] = [n];
    });

    return nodes.map((node, index) => {
      const column = Math.floor(index / 5);
      const row = index % 5;

      return {
        id: node.kp_id,
        type: "knowledgeNode",
        position: { x: column * 320, y: row * 140 },
        data: {
          label: node.title,
          mastery: node.mastery_level,
          bktPknow: node.bkt_p_know,
          difficulty: node.difficulty,
          isUnlocked: node.is_unlocked,
          isCurrent: node.kp_id === currentKpId,
        },
      };
    });
  }, [nodes, currentKpId]);

  const flowEdges: Edge[] = useMemo(() => {
    const edges: Edge[] = [];
    for (let i = 1; i < nodes.length; i++) {
      if (nodes[i].is_unlocked || nodes[i - 1].is_unlocked) {
        edges.push({
          id: `${nodes[i - 1].kp_id}-${nodes[i].kp_id}`,
          source: nodes[i - 1].kp_id,
          target: nodes[i].kp_id,
          animated: nodes[i].is_current,
          style: {
            stroke: nodes[i].is_unlocked ? "#6366f1" : "#334155",
            strokeWidth: 2,
          },
        });
      }
    }
    return edges;
  }, [nodes]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const kpNode = nodes.find((n) => n.kp_id === node.id);
      if (kpNode?.is_unlocked) onSelectKp(node.id);
    },
    [nodes, onSelectKp]
  );

  return (
    <div className="knowledge-graph" style={{ height: "calc(100vh - 200px)", minHeight: 500 }}>
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#334155" gap={20} />
        <Controls
          style={{ background: "#1e293b", borderColor: "#334155" }}
        />
        <MiniMap
          nodeColor={(node) => MASTERY_COLORS[node.data?.mastery as string] || "#94a3b8"}
          style={{ background: "#0f172a", borderColor: "#334155" }}
        />
      </ReactFlow>
    </div>
  );
}
