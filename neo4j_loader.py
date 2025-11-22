import os
import csv
from neo4j import GraphDatabase
from dotenv import load_dotenv
import networkx as nx
import matplotlib.pyplot as plt

load_dotenv()

driver = GraphDatabase.driver(
    os.environ.get("NEO4J_URI"),
    auth=(os.environ.get("NEO4J_USER"), os.environ.get("NEO4J_PASSWORD"))
)

def setup_indexes():
    """Create indexes and constraints for better performance"""
    with driver.session() as session:
        # Create constraints
        try:
            session.run("CREATE CONSTRAINT country_name IF NOT EXISTS FOR (c:Country) REQUIRE c.name IS UNIQUE")
            session.run("CREATE CONSTRAINT location_id IF NOT EXISTS FOR (l:Location) REQUIRE l.id IS UNIQUE")
            print(" Constraints created")
        except Exception as e:
            print(f"Constraints may already exist: {e}")
        
        # Create full-text search index
        try:
            session.run("""
                CREATE FULLTEXT INDEX locationFullTextIndex IF NOT EXISTS
                FOR (l:Location) ON EACH [l.name, l.description, l.type]
            """)
            print("Full-text index created")
        except Exception as e:
            print(f"Full-text index may already exist: {e}")

def clear_database():
    """Clear all nodes and relationships (use with caution)"""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        print("  Database cleared")

def load_locations(csv_path="data/locations.csv"):
    """Load locations from CSV into Neo4j"""
    if not os.path.exists(csv_path):
        print(f" CSV file not found: {csv_path}")
        return
    
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Loading {len(rows)} locations...")
    
    with driver.session() as session:
        for row in rows:
            session.execute_write(create_location, row)
    
    print(f" Loaded {len(rows)} locations into Neo4j")

def create_location(tx, row):
    """Create location node with relationships"""
    # Ensure required fields exist
    location_id = row.get('id', row.get('name', 'unknown'))
    name = row.get('name', 'Unknown')
    country = row.get('country', 'Unknown')
    
    tx.run("""
        MERGE (c:Country {name: $country})
        MERGE (l:Location {id: $id})
        SET l.name = $name, 
            l.type = $type, 
            l.description = $description,
            l.lat = toFloat($lat), 
            l.lon = toFloat($lon),
            l.rating = toFloat($rating),
            l.tags = $tags
        MERGE (l)-[:IN_COUNTRY]->(c)
        """, {
            'id': location_id,
            'name': name,
            'country': country,
            'type': row.get('type', ''),
            'description': row.get('description', ''),
            'lat': row.get('lat', '0'),
            'lon': row.get('lon', '0'),
            'rating': row.get('rating', '0'),
            'tags': row.get('tags', '')
        })

def create_relationships():
    """Create additional relationships based on location attributes"""
    with driver.session() as session:
        # Create relationships between locations of similar types
        session.run("""
            MATCH (l1:Location), (l2:Location)
            WHERE l1.type = l2.type AND l1.id < l2.id AND l1.type <> ''
            MERGE (l1)-[:SIMILAR_TYPE]->(l2)
        """)
        
        # Create relationships for locations in same country
        session.run("""
            MATCH (l1:Location)-[:IN_COUNTRY]->(c:Country)<-[:IN_COUNTRY]-(l2:Location)
            WHERE l1.id < l2.id
            MERGE (l1)-[:SAME_COUNTRY]->(l2)
        """)
        
        print(" Created additional relationships")

def get_statistics():
    """Print database statistics"""
    with driver.session() as session:
        # Count nodes
        result = session.run("MATCH (l:Location) RETURN count(l) as count")
        location_count = result.single()['count']
        
        result = session.run("MATCH (c:Country) RETURN count(c) as count")
        country_count = result.single()['count']
        
        # Count relationships
        result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = result.single()['count']
        
        print(f"\n Database Statistics:")
        print(f"   Locations: {location_count}")
        print(f"   Countries: {country_count}")
        print(f"   Relationships: {rel_count}")

def visualize(limit=50):
    """Visualize the location graph"""
    with driver.session() as s:
        res = s.run("""
            MATCH (l:Location)-[:IN_COUNTRY]->(c:Country)
            RETURN l.name AS loc, c.name AS country, l.type AS type LIMIT $limit
        """, {"limit": limit})
        
        G = nx.Graph()
        locations = []
        countries = []
        
        for r in res:
            loc_label = f"{r['loc']}\n({r['type']})" if r['type'] else r['loc']
            locations.append(loc_label)
            countries.append(r['country'])
            G.add_edge(loc_label, r['country'])
        
        # Create layout
        pos = nx.spring_layout(G, k=2, iterations=50)
        
        # Draw nodes
        plt.figure(figsize=(15, 10))
        
        # Draw country nodes (larger, different color)
        country_nodes = set(countries)
        nx.draw_networkx_nodes(G, pos, nodelist=country_nodes, 
                               node_color='lightblue', node_size=1500, alpha=0.8)
        
        # Draw location nodes
        location_nodes = set(locations)
        nx.draw_networkx_nodes(G, pos, nodelist=location_nodes,
                               node_color='lightcoral', node_size=800, alpha=0.7)
        
        # Draw edges and labels
        nx.draw_networkx_edges(G, pos, alpha=0.3)
        nx.draw_networkx_labels(G, pos, font_size=8)
        
        plt.title("Travel Knowledge Graph (Locations → Countries)", fontsize=16)
        plt.axis('off')
        plt.tight_layout()
        plt.savefig('knowledge_graph.png', dpi=300, bbox_inches='tight')
        print(" Graph visualization saved to 'knowledge_graph.png'")
        plt.show()

if __name__ == "__main__":
    print(" Starting Neo4j data loading...")
    
    # Setup database
    setup_indexes()
    
    # Optional: Clear existing data
    # clear_database()
    
    # Load data
    load_locations("data/locations.csv")
    
    # Create additional relationships
    create_relationships()
    
    # Show statistics
    get_statistics()
    
    # Visualize
    visualize(limit=30)
    
    driver.close()