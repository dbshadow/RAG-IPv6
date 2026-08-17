"""Knowledge Graph storage and management for Fast-GraphRAG."""

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    id: str  # Unique identifier (e.g. "rfc8200", "SLAAC", "Hop-by-Hop")
    name: str  # Display name
    type: str  # "rfc", "protocol", "header", "mechanism", "flag", "concept"
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    relation: str  # "OBSOLETES", "UPDATES", "DEFINES", "USES", "EXTENDS", "REFERENCES", "CONFLICTS_WITH"
    description: str = ""
    source_rfc: str = ""  # RFC citing or defining this relation
    weight: float = 1.0


class KnowledgeGraphStore:
    """In-memory Knowledge Graph with JSON persistence in data/graph/."""

    def __init__(self, graph_dir: Optional[Path] = None) -> None:
        self.graph_dir = graph_dir or settings.graph_dir
        self.graph_file = self.graph_dir / "graph_data.json"
        self.entity_embeddings_file = self.graph_dir / "entity_embeddings.json"

        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        # Adjacency mappings for rapid traversal
        self.adj_out: Dict[str, List[GraphEdge]] = {}
        self.adj_in: Dict[str, List[GraphEdge]] = {}
        self.entity_embeddings: Dict[str, List[float]] = {}

        self.load()

    def add_node(self, node: GraphNode) -> None:
        """Add or update a node in the graph."""
        clean_id = node.id.strip().lower()
        node.id = clean_id
        if clean_id not in self.nodes:
            self.nodes[clean_id] = node
            self.adj_out[clean_id] = []
            self.adj_in[clean_id] = []
        else:
            # Merge description if new one is longer/richer
            existing = self.nodes[clean_id]
            if len(node.description) > len(existing.description):
                existing.description = node.description
            existing.properties.update(node.properties)

    def add_edge(self, edge: GraphEdge) -> None:
        """Add a directed edge between nodes."""
        s = edge.source.strip().lower()
        t = edge.target.strip().lower()
        edge.source = s
        edge.target = t

        # Ensure endpoints exist
        if s not in self.nodes:
            self.add_node(GraphNode(id=s, name=s, type="concept"))
        if t not in self.nodes:
            self.add_node(GraphNode(id=t, name=t, type="concept"))

        # Avoid exact duplicate edge
        for existing in self.adj_out[s]:
            if existing.target == t and existing.relation.upper() == edge.relation.upper():
                if edge.description and not existing.description:
                    existing.description = edge.description
                return

        self.edges.append(edge)
        self.adj_out[s].append(edge)
        self.adj_in[t].append(edge)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self.nodes.get(node_id.strip().lower())

    def get_neighbors(self, node_id: str, direction: str = "both") -> List[GraphEdge]:
        clean_id = node_id.strip().lower()
        res = []
        if direction in ("out", "both") and clean_id in self.adj_out:
            res.extend(self.adj_out[clean_id])
        if direction in ("in", "both") and clean_id in self.adj_in:
            res.extend(self.adj_in[clean_id])
        return res

    def save(self) -> None:
        """Persist graph nodes and edges to disk."""
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "nodes": [asdict(n) for n in self.nodes.values()],
            "edges": [asdict(e) for e in self.edges],
        }
        self.graph_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        if self.entity_embeddings:
            self.entity_embeddings_file.write_text(
                json.dumps(self.entity_embeddings), encoding="utf-8"
            )
        logger.info(
            "Saved Knowledge Graph with %d nodes and %d edges to %s",
            len(self.nodes),
            len(self.edges),
            self.graph_file,
        )

    def load(self) -> None:
        """Load graph nodes and edges from disk if exists."""
        if not self.graph_file.exists():
            return
        try:
            raw = json.loads(self.graph_file.read_text(encoding="utf-8"))
            for n_dict in raw.get("nodes", []):
                node = GraphNode(**n_dict)
                self.add_node(node)
            for e_dict in raw.get("edges", []):
                edge = GraphEdge(**e_dict)
                self.add_edge(edge)
            if self.entity_embeddings_file.exists():
                self.entity_embeddings = json.loads(
                    self.entity_embeddings_file.read_text(encoding="utf-8")
                )
            logger.info(
                "Loaded Knowledge Graph with %d nodes and %d edges from %s",
                len(self.nodes),
                len(self.edges),
                self.graph_file,
            )
        except Exception as e:
            logger.error("Failed to load graph data: %s", e)

    def stats(self) -> Dict[str, Any]:
        """Return graph statistics."""
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "embedded_entities": len(self.entity_embeddings),
            "node_types": {
                ntype: sum(1 for n in self.nodes.values() if n.type == ntype)
                for ntype in set(n.type for n in self.nodes.values())
            },
            "relation_types": {
                rtype: sum(1 for e in self.edges if e.relation == rtype)
                for rtype in set(e.relation for e in self.edges)
            },
        }
