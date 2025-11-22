"""
Integration tests for Blue Enigma Hybrid AI System (Groq Version)
Run this after setting up Neo4j, Pinecone, and loading data.
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pinecone import Pinecone
from groq import Groq

load_dotenv()


# ---------------------------------------------------------
# TEST 1: Environment Variables
# ---------------------------------------------------------
def test_env_variables():
    print("\n Testing Environment Variables...")

    required_vars = [
        "GROQ_API_KEY",
        "PINECONE_API_KEY",
        "NEO4J_URI",
        "NEO4J_USER",
        "NEO4J_PASSWORD"
    ]

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
            print(f"    {var}: Not set")
        else:
            preview = value[:10] + "..." if len(value) > 10 else value
            print(f"    {var}: {preview}")

    if missing:
        print(f"\n  Missing variables: {', '.join(missing)}")
        return False

    print("\n All environment variables set")
    return True


# ---------------------------------------------------------
# TEST 2: Neo4j Connection
# ---------------------------------------------------------
def test_neo4j_connection():
    print("\n Testing Neo4j Connection...")

    try:
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )

        with driver.session() as session:
            r = session.run("RETURN 1 AS num")
            if r.single()["num"] != 1:
                raise ValueError("Unexpected Neo4j response")

        print("    Connection successful")

        with driver.session() as session:
            loc = session.run("MATCH (l:Location) RETURN count(l) AS c").single()["c"]
            cty = session.run("MATCH (c:Country) RETURN count(c) AS c").single()["c"]

            print(f"    Locations: {loc}")
            print(f"    Countries: {cty}")

            if loc == 0:
                print("    No locations found. Run neo4j_loader.py first")
                return False

        driver.close()
        print("\n Neo4j connection and data verified")
        return True

    except Exception as e:
        print(f"    Connection failed: {e}")
        print("    Make sure Neo4j is running: docker-compose up -d")
        return False


# ---------------------------------------------------------
# TEST 3: Pinecone Connection
# ---------------------------------------------------------
def test_pinecone_connection():
    print("\n Testing Pinecone Connection...")

    try:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        indexes = pc.list_indexes()

        print("    Connection successful")
        print(f"    Available indexes: {[i.name for i in indexes]}")

        index_name = os.getenv("PINECONE_INDEX_NAME", "travel-docs")

        if index_name not in [i.name for i in indexes]:
            print(f"    Index '{index_name}' not found. Run pinecone_upload.py first")
            return False

        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        vectors = stats.get("total_vector_count", 0)

        print(f"    Vectors in '{index_name}': {vectors}")

        if vectors == 0:
            print("    No vectors found. Run pinecone_upload.py first")
            return False

        print("\n Pinecone connection and data verified")
        return True

    except Exception as e:
        print(f"    Connection failed: {e}")
        return False


# ---------------------------------------------------------
# TEST 4: GROQ Chat API
# ---------------------------------------------------------
def test_groq_connection():
    print("\n Testing Groq API...")

    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        model = os.getenv("GROQ_CHAT_MODEL")

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "test connection"}],
            max_tokens=10
        )

        msg = response.choices[0].message["content"]
        print(f"    Groq reply: {msg}")
        print("\n Groq API verified")
        return True

    except Exception as e:
        print(f"    Connection failed: {e}")
        print("    Model probably decommissioned. Update GROQ_CHAT_MODEL in .env")
        return False



# ---------------------------------------------------------
# TEST 5: Neo4j Full-Text Index
# ---------------------------------------------------------
def test_full_text_index():
    print("\n Testing Neo4j Full-Text Index...")

    try:
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )

        with driver.session() as session:
            res = session.run("SHOW INDEXES")
            indexes = [r["name"] for r in res]

            if "locationFullTextIndex" not in indexes:
                print("    Full-text index missing. Run neo4j_loader.py")
                return False

            print("    Index exists")

            q = session.run("""
                CALL db.index.fulltext.queryNodes('locationFullTextIndex', 'restaurant')
                YIELD node, score
                RETURN node.name AS name LIMIT 3
            """)

            found = [rec["name"] for rec in q]
            print(f"    Search results: {found}")

        driver.close()
        print("\n Full-text index verified")
        return True

    except Exception as e:
        print(f"    Test failed: {e}")
        return False


# ---------------------------------------------------------
# TEST 6: Hybrid Search System
# ---------------------------------------------------------
def test_hybrid_search():
    print("\n Testing Hybrid Search System...")

    try:
        from hybrid_chat import answer

        query = "best restaurants in Delhi"
        print(f"    Query: {query}")

        result = answer(query, verbose=False)

        if not result or len(result) < 50:
            print("    Response is empty or too short")
            return False

        print("    Hybrid search produced a valid response")
        return True

    except Exception as e:
        print(f"    Search failed: {e}")
        return False


# ---------------------------------------------------------
# RUN ALL TESTS
# ---------------------------------------------------------
def run_all_tests():
    print("=" * 60)
    print("BLUE ENIGMA SYSTEM TESTS")
    print("=" * 60)

    tests = [
        ("Environment Variables", test_env_variables),
        ("Neo4j Connection", test_neo4j_connection),
        ("Pinecone Connection", test_pinecone_connection),
        ("Groq API", test_groq_connection),
        ("Neo4j Full-Text Index", test_full_text_index),
        ("Hybrid Search System", test_hybrid_search),
    ]

    results = []

    for name, fn in tests:
        try:
            result = fn()
            results.append((name, result))
        except Exception as e:
            print(f"    {name} crashed: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, r in results:
        print(f"{'PASS' if r else 'FAIL'}: {name}")

    print("\nResults:", passed, "/", total)

    if passed == total:
        print("All tests passed. System is ready to use.")
        print("Next steps:")
        print("  1. Run interactive chat: python hybrid_chat.py")
        print("  2. Start API server: python fastapi_app.py")
    else:
        print("Some tests failed. Fix issues before using the system.")
        print("Common fixes:")
        print("  - Start Neo4j: docker-compose up -d")
        print("  - Load data: python neo4j_loader.py && python pinecone_upload.py")
        print("  - Check .env file for correct keys")

    print("=" * 60)
    return passed == total


if __name__ == "__main__":
    ok = run_all_tests()
    exit(0 if ok else 1)
