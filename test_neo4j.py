import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

print("=" * 60)
print("NEO4J CONNECTION TEST")
print("=" * 60)

# Display configuration
neo4j_uri = os.getenv('NEO4J_URI')
neo4j_user = os.getenv('NEO4J_USER')
neo4j_password = os.getenv('NEO4J_PASSWORD')

print("\n Configuration:")
print(f"   URI: {neo4j_uri}")
print(f"   User: {neo4j_user}")
print(f"   Password: {'*' * len(neo4j_password) if neo4j_password else 'NOT SET'}")

# Check if credentials are set
if not neo4j_uri or not neo4j_user or not neo4j_password:
    print("\n ERROR: Missing credentials in .env file!")
    print("\nPlease ensure your .env file contains:")
    print("NEO4J_URI=bolt://localhost:7687")
    print("NEO4J_USER=neo4j")
    print("NEO4J_PASSWORD=your_password")
    exit(1)

print("\n Testing connection...")

try:
    # Try to connect
    driver = GraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password)
    )
    
    # Verify connectivity
    driver.verify_connectivity()
    print(" Connection established!")
    
    # Test a simple query
    print("\n🔍 Testing query execution...")
    with driver.session() as session:
        result = session.run("RETURN 1 as num, 'Hello Neo4j' as message")
        record = result.single()
        print(f" Query successful!")
        print(f"   Result: num={record['num']}, message={record['message']}")
        
        # Get Neo4j version
        result = session.run("CALL dbms.components() YIELD versions RETURN versions[0] as version")
        version = result.single()['version']
        print(f"   Neo4j Version: {version}")
    
    # Get database stats
    print("\n Database Statistics:")
    with driver.session() as session:
        # Count nodes
        result = session.run("MATCH (n) RETURN count(n) as count")
        node_count = result.single()['count']
        print(f"   Total Nodes: {node_count}")
        
        # Count relationships
        result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = result.single()['count']
        print(f"   Total Relationships: {rel_count}")
    
    driver.close()
    
    print("\n" + "=" * 60)
    print(" ALL TESTS PASSED! Neo4j is ready to use.")
    print("=" * 60)
    print("\n You can now run: python load_to_neo4j.py")
    
except Exception as e:
    print(f"\n CONNECTION FAILED!")
    print(f"   Error: {e}")
    
    print("\n Troubleshooting Steps:")
    print("\n1. Check if Neo4j is running:")
    print("   docker ps | findstr neo4j")
    
    print("\n2. If not running, start it:")
    print("   docker-compose up -d")
    print("   Start-Sleep -Seconds 30")
    
    print("\n3. Try to access Neo4j Browser:")
    print("   http://localhost:7474")
    print("   Default credentials: neo4j/neo4j")
    
    print("\n4. If password is wrong, reset Neo4j:")
    print("   docker-compose down")
    print("   docker volume rm (docker volume ls -q | findstr neo4j)")
    print("   # Edit docker-compose.yml: NEO4J_AUTH=neo4j/password123")
    print("   docker-compose up -d")
    print("   # Update .env: NEO4J_PASSWORD=password123")
    
    print("\n5. Check your .env file:")
    print("   Make sure there are NO spaces around = and NO quotes")
    print("   Correct: NEO4J_PASSWORD=mypassword")
    print("   Wrong:   NEO4J_PASSWORD = \"mypassword\"")
    
    print("\n6. Verify .env file location:")
    env_path = os.path.join(os.getcwd(), '.env')
    if os.path.exists(env_path):
        print(f"    .env found at: {env_path}")
    else:
        print(f"    .env NOT found at: {env_path}")
        print("   Create .env from .env.example")
    
    exit(1)