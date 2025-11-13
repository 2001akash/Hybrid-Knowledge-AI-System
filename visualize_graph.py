import networkx as nx
import matplotlib.pyplot as plt
from neo4j import GraphDatabase
import config

driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))

def fetch(limit=50):
    with driver.session() as session:
        res = session.run("""
            MATCH (a:Entity)-[r]-(b:Entity)
            RETURN a.name AS a, a.id AS aid, b.name AS b, b.id AS bid, type(r) AS rel
            LIMIT $limit
        """, {"limit": limit})
        return list(res)

def build_graph(records):
    G = nx.Graph()
    for r in records:
        A = f"{r['a']} ({r['aid']})"
        B = f"{r['b']} ({r['bid']})"
        G.add_node(A)
        G.add_node(B)
        G.add_edge(A, B, label=r['rel'])
    return G

if __name__ == "__main__":
    recs = fetch()
    G = build_graph(recs)
    plt.figure(figsize=(14, 12))
    pos = nx.spring_layout(G, seed=42)
    nx.draw(G, pos, with_labels=True, node_size=1200, font_size=8)
    plt.title("Travel Graph (Neo4j)")
    plt.savefig("neo4j_graph.png", dpi=200)
    print("✔ Saved graph to neo4j_graph.png")
