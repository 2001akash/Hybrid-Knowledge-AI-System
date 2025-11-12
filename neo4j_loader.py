import os, csv
from neo4j import GraphDatabase
from dotenv import load_dotenv
import networkx as nx
import matplotlib.pyplot as plt

load_dotenv()

driver = GraphDatabase.driver(
    os.environ.get("NEO4J_URI"),
    auth=(os.environ.get("NEO4J_USER"), os.environ.get("NEO4J_PASSWORD"))
)

def load_locations(csv_path):
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    with driver.session() as session:
        for row in rows:
            session.write_transaction(create_location, row)

def create_location(tx, row):
    tx.run("""
        MERGE (c:Country {name: $country})
        MERGE (l:Location {id: $id})
        SET l.name=$name, l.type=$type, l.description=$description,
            l.lat=toFloat($lat), l.lon=toFloat($lon)
        MERGE (l)-[:IN_COUNTRY]->(c)
        """, row)

def visualize(limit=50):
    with driver.session() as s:
        res = s.run("""
            MATCH (l:Location)-[:IN_COUNTRY]->(c:Country)
            RETURN l.name AS loc, c.name AS country LIMIT $limit
        """, {"limit": limit})
        G = nx.Graph()
        for r in res:
            G.add_edge(r["loc"], r["country"])
        nx.draw(G, with_labels=True, node_size=800)
        plt.title("Sample Location Graph")
        plt.show()

if __name__ == "__main__":
    load_locations("data/locations.csv")
    visualize()
