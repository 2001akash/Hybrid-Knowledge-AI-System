"""
Integration tests for Blue Enigma Hybrid AI System
Run this after setting up Neo4j, Pinecone, and loading data
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pinecone import Pinecone
from openai import OpenAI

load_dotenv()

def test_env_variables():
    """Test that all required environment variables are set"""
    print("\n🔍 Testing Environment Variables...")
    
    required_vars = [
        "OPENAI_API_KEY",
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
            print(f"   ❌ {var}: Not set")
        else:
            # Show first 10 chars for security
            preview = value[:10] + "..." if len(value) > 10 else value
            print(f"   ✅ {var}: {preview}")
    
    if missing:
        print(f"\n⚠️  Missing variables: {', '.join(missing)}")
        return False
    
    print("\n✅ All environment variables set!")
    return True

def test_neo4j_connection():
    """Test Neo4j database connection"""
    print("\n🔍 Testing Neo4j Connection...")
    
    try:
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )
        
        with driver.session() as session:
            result = session.run("RETURN 1 as num")
            record = result.single()
            assert record["num"] == 1
        
        print("   ✅ Connection successful")
        
        # Check data
        with driver.session() as session:
            result = session.run("MATCH (l:Location) RETURN count(l) as count")
            location_count = result.single()["count"]
            
            result = session.run("MATCH (c:Country) RETURN count(c) as count")
            country_count = result.single()["count"]
            
            print(f"   📊 Locations: {location_count}")
            print(f"   📊 Countries: {country_count}")
            
            if location_count == 0:
                print("   ⚠️  No locations found. Run neo4j_loader.py first!")
                return False
        
        driver.close()
        print("\n✅ Neo4j connection and data verified!")
        return True
        
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        print("   💡 Make sure Neo4j is running: docker-compose up -d")
        return False

def test_pinecone_connection():
    """Test Pinecone connection and index"""
    print("\n🔍 Testing Pinecone Connection...")
    
    try:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        indexes = pc.list_indexes()
        
        print(f"   ✅ Connection successful")
        print(f"   📊 Available indexes: {[idx.name for idx in indexes]}")
        
        index_name = os.getenv("PINECONE_INDEX_NAME", "travel-docs")
        
        if index_name in [idx.name for idx in indexes]:
            index = pc.Index(index_name)
            stats = index.describe_index_stats()
            vector_count = stats.get('total_vector_count', 0)
            
            print(f"   📊 Vectors in '{index_name}': {vector_count}")
            
            if vector_count == 0:
                print("   ⚠️  No vectors found. Run pinecone_upload.py first!")
                return False
        else:
            print(f"   ⚠️  Index '{index_name}' not found. Run pinecone_upload.py first!")
            return False
        
        print("\n✅ Pinecone connection and data verified!")
        return True
        
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

def test_openai_connection():
    """Test OpenAI API connection"""
    print("\n🔍 Testing OpenAI Connection...")
    
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Test embedding
        response = client.embeddings.create(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            input="test"
        )
        
        embedding = response.data[0].embedding
        print(f"   ✅ Embedding API works (dimension: {len(embedding)})")
        
        # Test chat
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": "Say 'test successful'"}],
            max_tokens=10
        )
        
        message = response.choices[0].message.content
        print(f"   ✅ Chat API works: '{message}'")
        
        print("\n✅ OpenAI API verified!")
        return True
        
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

def test_hybrid_search():
    """Test the hybrid search system"""
    print("\n🔍 Testing Hybrid Search System...")
    
    try:
        from hybrid_chat import answer
        
        test_query = "best restaurants in Delhi"
        print(f"   🔎 Query: '{test_query}'")
        
        result = answer(test_query, verbose=False)
        
        if result and len(result) > 50:
            print(f"   ✅ Response generated ({len(result)} characters)")
            print(f"\n   Preview:\n   {result[:200]}...\n")
        else:
            print(f"   ⚠️  Response too short or empty")
            return False
        
        print("✅ Hybrid search system working!")
        return True
        
    except Exception as e:
        print(f"   ❌ Search failed: {e}")
        return False

def test_full_text_index():
    """Test Neo4j full-text index"""
    print("\n🔍 Testing Neo4j Full-Text Index...")
    
    try:
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )
        
        with driver.session() as session:
            # Check if index exists
            result = session.run("SHOW INDEXES")
            indexes = [record["name"] for record in result]
            
            if "locationFullTextIndex" in indexes:
                print("   ✅ Full-text index exists")
                
                # Test search
                result = session.run("""
                    CALL db.index.fulltext.queryNodes('locationFullTextIndex', 'restaurant')
                    YIELD node, score
                    RETURN node.name AS name LIMIT 3
                """)
                
                results = [record["name"] for record in result]
                print(f"   ✅ Search works, found: {results}")
            else:
                print("   ⚠️  Full-text index not found. Run neo4j_loader.py!")
                return False
        
        driver.close()
        print("\n✅ Full-text index verified!")
        return True
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and provide summary"""
    print("=" * 60)
    print("🧪 BLUE ENIGMA SYSTEM TESTS")
    print("=" * 60)
    
    tests = [
        ("Environment Variables", test_env_variables),
        ("Neo4j Connection", test_neo4j_connection),
        ("Pinecone Connection", test_pinecone_connection),
        ("OpenAI API", test_openai_connection),
        ("Neo4j Full-Text Index", test_full_text_index),
        ("Hybrid Search System", test_hybrid_search),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System ready to use.")
        print("\nNext steps:")
        print("  1. Run interactive chat: python hybrid_chat.py")
        print("  2. Start API server: python fastapi_app.py")
    else:
        print("⚠️  Some tests failed. Please fix issues before using system.")
        print("\nCommon fixes:")
        print("  - Start Neo4j: docker-compose up -d")
        print("  - Load data: python neo4j_loader.py && python pinecone_upload.py")
        print("  - Check .env file has correct API keys")
    
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)