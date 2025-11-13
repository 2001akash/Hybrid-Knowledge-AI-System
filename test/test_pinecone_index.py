import config
from pinecone import Pinecone

def test_index_exists():
    pc = Pinecone(api_key=config.PINECONE_API_KEY)
    names = pc.list_indexes().names()
    assert config.PINECONE_INDEX_NAME in names
