import json
from neo4j import GraphDatabase
from tqdm import tqdm
import config

driver = GraphDatabase.driver(
    config.NEO4J_URI, 
    auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
)

def create_constraints(tx):
    """Create constraints for better performance and data integrity"""
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Location) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Country) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:City) REQUIRE n.name IS UNIQUE"
    ]
    
    for constraint in constraints:
        try:
            tx.run(constraint)
        except Exception as e:
            print(f"Constraint already exists or error: {e}")

def create_indexes(tx):
    """Create full-text search indexes"""
    try:
        tx.run("""
            CREATE FULLTEXT INDEX entityFullTextIndex IF NOT EXISTS
            FOR (n:Entity) ON EACH [n.name, n.description, n.type]
        """)
    except Exception as e:
        print(f"Index creation error: {e}")

def upsert_node(tx, node):
    """Create or update a node with all its properties"""
    labels = [node.get("type", "Entity"), "Entity"]
    props = {k: v for k, v in node.items() if k != "connections"}
    
    # Clean label names (remove spaces, special chars)
    clean_labels = [label.replace(" ", "_").replace("-", "_") for label in labels]
    
    tx.run(
        f"MERGE (n:{':'.join(clean_labels)} {{id:$id}}) SET n += $props",
        id=node["id"], props=props
    )

def create_relationship(tx, source_id, rel):
    """Create relationship between entities"""
    rel_type = rel.get("relation", "RELATED_TO").replace(" ", "_").replace("-", "_").upper()
    target = rel.get("target")
    
    if not target:
        return
    
    # Add relationship properties if available
    rel_props = {k: v for k, v in rel.items() if k not in ["relation", "target"]}
    
    if rel_props:
        tx.run(
            f"""
            MATCH (a:Entity {{id:$source_id}}), (b:Entity {{id:$target_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += $props
            """,
            source_id=source_id, target_id=target, props=rel_props
        )
    else:
        tx.run(
            f"""
            MATCH (a:Entity {{id:$source_id}}), (b:Entity {{id:$target_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            """,
            source_id=source_id, target_id=target
        )

def get_stats(tx):
    """Get database statistics"""
    stats = {}
    
    # Count nodes
    result = tx.run("MATCH (n:Entity) RETURN count(n) as count")
    stats['entities'] = result.single()['count']
    
    # Count relationships
    result = tx.run("MATCH ()-[r]->() RETURN count(r) as count")
    stats['relationships'] = result.single()['count']
    
    # Count by type
    result = tx.run("""
        MATCH (n:Entity)
        RETURN n.type as type, count(n) as count
        ORDER BY count DESC
    """)
    stats['by_type'] = {record['type']: record['count'] for record in result}
    
    return stats

def main():
    """Load Vietnam travel dataset into Neo4j"""
    dataset_file = "vietnam_travel_dataset.json"
    
    print(f"Loading data from {dataset_file}...")
    
    try:
        with open(dataset_file, "r", encoding="utf-8") as f:
            nodes = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {dataset_file}")
        print("Please ensure vietnam_travel_dataset.json exists in the current directory")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {dataset_file}: {e}")
        return
    
    print(f"Found {len(nodes)} nodes to process")
    
    with driver.session() as session:
        # Create constraints and indexes
        print("Creating constraints and indexes...")
        session.execute_write(create_constraints)
        session.execute_write(create_indexes)
        
        # Create all nodes first
        print("Creating nodes...")
        for node in tqdm(nodes, desc="Creating nodes"):
            try:
                session.execute_write(upsert_node, node)
            except Exception as e:
                print(f"Error creating node {node.get('id')}: {e}")
        
        # Create relationships
        print("Creating relationships...")
        for node in tqdm(nodes, desc="Creating relationships"):
            for rel in node.get("connections", []):
                try:
                    session.execute_write(create_relationship, node["id"], rel)
                except Exception as e:
                    print(f"Error creating relationship from {node.get('id')}: {e}")
        
        # Get and display statistics
        print("\n" + "="*50)
        print("Database Statistics")
        print("="*50)
        stats = session.execute_read(get_stats)
        print(f"Total Entities: {stats['entities']}")
        print(f"Total Relationships: {stats['relationships']}")
        print("\nEntities by Type:")
        for entity_type, count in stats['by_type'].items():
            print(f"  - {entity_type}: {count}")
    
    print("\n✅ Successfully loaded all data into Neo4j!")
    driver.close()

if __name__ == "__main__":
    main()