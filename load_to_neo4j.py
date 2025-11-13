import json
from neo4j import GraphDatabase
from tqdm import tqdm
import config

driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))

def create_constraints(tx):
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE")

def upsert_node(tx, node):
    labels = [node.get("type", "Entity"), "Entity"]
    props = {k: v for k, v in node.items() if k != "connections"}
    tx.run(
        f"MERGE (n:{':'.join(labels)} {{id:$id}}) SET n += $props",
        id=node["id"], props=props
    )

def create_relationship(tx, source_id, rel):
    rel_type = rel.get("relation", "RELATED_TO")
    target = rel.get("target")
    if not target:
        return
    tx.run(
        f"""
        MATCH (a:Entity {{id:$source_id}}), (b:Entity {{id:$target_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        """,
        source_id=source_id, target_id=target
    )

def main():
    with open("vietnam_travel_dataset.json", "r", encoding="utf-8") as f:
        nodes = json.load(f)

    with driver.session() as session:
        session.execute_write(create_constraints)

        for node in tqdm(nodes, desc="Creating nodes"):
            session.execute_write(upsert_node, node)

        for node in tqdm(nodes, desc="Creating relationships"):
            for rel in node.get("connections", []):
                session.execute_write(create_relationship, node["id"], rel)

    print("✔ Loaded all data into Neo4j.")

if __name__ == "__main__":
    main()
