"""Personalized PageRank (PPR) Graph Traverser for Fast-GraphRAG."""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from app.graph.store import GraphEdge, GraphNode, KnowledgeGraphStore
from app.indexer.embedder import OllamaEmbedder

logger = logging.getLogger(__name__)


class GraphTraverser:
    """Extracts relevant subgraphs using entity embedding seed discovery and Personalized PageRank."""

    def __init__(
        self,
        store: Optional[KnowledgeGraphStore] = None,
        embedder: Optional[OllamaEmbedder] = None,
    ) -> None:
        self.store = store or KnowledgeGraphStore()
        self.embedder = embedder or OllamaEmbedder()

    async def find_seed_entities(
        self,
        query: str,
        top_n: int = 5,
        threshold: float = 0.45,
    ) -> List[Tuple[str, float]]:
        """Identify matching seed entity nodes from the query string and semantic embedding."""
        clean_q = query.lower()
        matched_seeds: Dict[str, float] = {}

        # 1. Exact / Substring keyword matching on entity names & aliases
        for node_id, node in self.store.nodes.items():
            n_name = node.name.lower()
            if n_name in clean_q or (len(node_id) >= 3 and node_id in clean_q):
                matched_seeds[node_id] = 1.0

        # Check for RFC mentions (e.g. "RFC 8200", "rfc 2460", "8200")
        import re
        for m in re.findall(r"(?:rfc\s*(\d+)|(\d{4}))", clean_q):
            num = m[0] or m[1]
            rfc_key = f"rfc{num}".lower()
            if rfc_key in self.store.nodes:
                matched_seeds[rfc_key] = 1.5  # Boost explicitly mentioned RFCs

        # 2. Semantic Embedding search if entity embeddings exist
        if self.store.entity_embeddings:
            try:
                q_emb = await self.embedder.get_embedding(query)
                q_vec = np.array(q_emb, dtype=np.float32)
                q_norm = np.linalg.norm(q_vec)

                for e_id, e_vec_list in self.store.entity_embeddings.items():
                    e_vec = np.array(e_vec_list, dtype=np.float32)
                    denom = q_norm * np.linalg.norm(e_vec)
                    if denom > 0:
                        sim = float(np.dot(q_vec, e_vec) / denom)
                        if sim >= threshold and (e_id not in matched_seeds or sim > matched_seeds[e_id]):
                            matched_seeds[e_id] = sim
            except Exception as e:
                logger.warning("Failed semantic seed matching: %s", e)

        # Sort and take top_n
        sorted_seeds = sorted(matched_seeds.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return sorted_seeds

    def personalized_pagerank(
        self,
        seed_scores: Dict[str, float],
        alpha: float = 0.85,
        max_iter: int = 40,
        tol: float = 1e-5,
    ) -> Dict[str, float]:
        """Compute Personalized PageRank (PPR) distribution across the graph starting from seed nodes."""
        nodes = list(self.store.nodes.keys())
        if not nodes or not seed_scores:
            return {}

        n_count = len(nodes)
        node_to_idx = {nid: i for i, nid in enumerate(nodes)}

        # Personalization teleport vector
        p = np.zeros(n_count, dtype=np.float32)
        total_seed_weight = sum(seed_scores.values())
        for nid, score in seed_scores.items():
            if nid in node_to_idx:
                p[node_to_idx[nid]] = score / total_seed_weight

        # Build Transition Matrix
        M = np.zeros((n_count, n_count), dtype=np.float32)
        for s_id, edges in self.store.adj_out.items():
            if s_id not in node_to_idx or not edges:
                continue
            s_idx = node_to_idx[s_id]
            valid_targets = [e.target for e in edges if e.target in node_to_idx]
            if valid_targets:
                weight = 1.0 / len(valid_targets)
                for t_id in valid_targets:
                    t_idx = node_to_idx[t_id]
                    M[t_idx, s_idx] = weight  # Column-stochastic transition

        # Dangling node handling
        dangling_nodes = [node_to_idx[nid] for nid, edges in self.store.adj_out.items() if not edges]

        # Power iteration
        v = p.copy()
        for _ in range(max_iter):
            v_prev = v.copy()
            dangling_sum = sum(v_prev[d] for d in dangling_nodes)
            v = alpha * (M @ v_prev + dangling_sum * p) + (1.0 - alpha) * p

            # Check convergence
            if np.sum(np.abs(v - v_prev)) < tol:
                break

        res = {nodes[i]: float(v[i]) for i in range(n_count) if v[i] > 0}
        return res

    async def retrieve_subgraph(
        self,
        query: str,
        max_nodes: int = 8,
        max_edges: int = 12,
    ) -> Dict[str, Any]:
        """Retrieve most relevant connected subgraph for query context augmentation."""
        seeds = await self.find_seed_entities(query, top_n=5)
        if not seeds:
            return {"nodes": [], "edges": [], "triples_text": "", "citations": []}

        seed_dict = {nid: score for nid, score in seeds}
        ppr_scores = self.personalized_pagerank(seed_dict)

        # Select Top nodes
        sorted_nodes = sorted(ppr_scores.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
        selected_node_ids = set(nid for nid, _ in sorted_nodes)

        # Extract interconnecting edges
        selected_edges: List[GraphEdge] = []
        citations: List[Dict[str, Any]] = []
        seen_rfcs: Set[str] = set()

        for s_id in selected_node_ids:
            for edge in self.store.adj_out.get(s_id, []):
                if edge.target in selected_node_ids:
                    selected_edges.append(edge)
                    if edge.source_rfc and edge.source_rfc not in seen_rfcs:
                        seen_rfcs.add(edge.source_rfc)
                        rfc_node = self.store.get_node(f"rfc{edge.source_rfc}")
                        citations.append(
                            {
                                "rfc_number": edge.source_rfc,
                                "rfc_id": f"rfc{edge.source_rfc}",
                                "rfc_title": rfc_node.properties.get("title", f"RFC {edge.source_rfc}")
                                if rfc_node
                                else f"RFC {edge.source_rfc}",
                                "relation": edge.relation,
                                "citation_label": f"RFC {edge.source_rfc} ({edge.relation})",
                                "datatracker_url": f"https://datatracker.ietf.org/doc/rfc{edge.source_rfc}/",
                            }
                        )

        # Truncate edges if too many
        selected_edges = selected_edges[:max_edges]

        # Format into clean Knowledge Graph Context text
        triples_lines = []
        for e in selected_edges:
            s_name = self.store.get_node(e.source).name if self.store.get_node(e.source) else e.source
            t_name = self.store.get_node(e.target).name if self.store.get_node(e.target) else e.target
            desc = f" ({e.description})" if e.description else ""
            src_rfc = f" [RFC {e.source_rfc}]" if e.source_rfc else ""
            triples_lines.append(f"• ({s_name}) ──[{e.relation}]──> ({t_name}){desc}{src_rfc}")

        triples_text = "\n".join(triples_lines) if triples_lines else ""

        return {
            "nodes": [
                {
                    "id": nid,
                    "name": self.store.get_node(nid).name if self.store.get_node(nid) else nid,
                    "type": self.store.get_node(nid).type if self.store.get_node(nid) else "concept",
                    "score": round(score, 4),
                }
                for nid, score in sorted_nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                    "description": e.description,
                    "source_rfc": e.source_rfc,
                }
                for e in selected_edges
            ],
            "triples_text": triples_text,
            "citations": citations,
        }
